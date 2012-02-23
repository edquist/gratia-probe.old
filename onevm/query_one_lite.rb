#!/usr/bin/env ruby
 
##############################################################################
# Environment Configuration
##############################################################################

ONE_LOCATION=ENV["ONE_LOCATION"]
 
if !ONE_LOCATION
    RUBY_LIB_LOCATION="/usr/lib/one/ruby"
else
    RUBY_LIB_LOCATION=ONE_LOCATION+"/lib/ruby"
end
 
$: << RUBY_LIB_LOCATION
 
##############################################################################
# Required libraries
##############################################################################

require 'pp'
require 'optparse'
require 'OpenNebula'
require 'OpenNebula/Pool'
 
include OpenNebula
 
##############################################################################
# Classes
##############################################################################

class OpenNebulaSensorCache

    attr_reader :is_valid, :queued_vm_ids, :last_known_id, :etime, :filename


    # Class constructor
    def initialize(rtime=Time.now().to_i(), stime=0, etime=0,
                   last_known_id=0, queued_vm_ids=[])
        @filename = nil
        @rtime = rtime
        @etime = etime
        @stime = stime
        @last_known_id = last_known_id
        @queued_vm_ids = queued_vm_ids
        @is_valid = false
        if stime > 0 and etime > 0 and last_known_id > 0
            @is_valid = true
        end
    end

    # String representation of the cache
    def to_s()
        str = "RUN_TIME=#{@rtime}" + "\n" +
              "RUN_STIME=#{@stime}" + "\n" + 
              "RUN_ETIME=#{@etime}" + "\n" + 
              "LAST_KNOWN_ID=#{@last_known_id}"
        if @queued_vm_ids.size() > 0
            str = str + "\n" + "QUEUED_VM_IDS=" + @queued_vm_ids.join(",")
            #str = str + "\n" + "QUEUED_VM_IDS=" + @queued_vm_ids
        end
        return str
    end


    # Store the cache to file
    def store(file)
        if @is_valid
            @filename = file
            cachefile = File.new(file, "w")
            cachefile.puts to_s()
            cachefile.close()
        end
    end


    # Load from file
    def load(file)
        info = {} 
        if File.exists?(file)
            begin 
                #puts "Using cachefile: #{file}"
                cachefile = File.new(file, "r")
                while (line = cachefile.gets())
                    tokens = line.split("=")
                    if tokens.size() > 1
                        field = tokens[0].strip()
                        value = tokens[1, tokens.size()-1].join("=").strip()
                        info[field] = value
                    end
                end
                cachefile.close()
                @filename = file
            rescue => err
                puts "Exception: #{err}"
                err
            end
        else
            puts "Cache file '#{file}' does not exist. Fetching info for all the VMs."
        end

        if info.has_key?("LAST_KNOWN_ID")
            @last_known_id = Integer(info["LAST_KNOWN_ID"])
        end
        
        if info.has_key?("RUN_TIME")
            @rtime = Integer(info["RUN_TIME"])
        end
        
        if info.has_key?("RUN_STIME")
            @stime = Integer(info["RUN_STIME"])
        end
        
        if info.has_key?("RUN_ETIME")
            @etime = Integer(info["RUN_ETIME"])
        end
        
        if info.has_key?("QUEUED_VM_IDS")
            info["QUEUED_VM_IDS"].split(",").each do |q_id|
                @queued_vm_ids << Integer(q_id.strip())
            end
            @queued_vm_ids.sort!
        end

        @is_valid = true
    end

end #OpenNebulaSensorCache


class OpenNebulaSensorCacheManager

    # Class constructor
    def initialize(cachedir="/var/tmp/one-gratia-history")
        @cachedir = cachedir
        @cache_prefix = @cachedir + "/cache."
        @caches = {}
    end
  

    # Find, load and return best available cache based on the etime
    def find(stime)
        # Look for cache file with etime <= stime
        ts = []
        files = Dir.glob(@cache_prefix + "*")
        files.each() do |f|
            tokens = f.split(".")
            if tokens.size() > 1
                # etime for the run is at the end of the filename
                ts << Integer(tokens[tokens.size() - 1])
            end
        end
        # Do a reverse sort
        ts.sort! {|x,y| y <=> x}
    
        # We can be smart here and do O(log(n)) but thats for future
        et = 0
        ts.each() do |t|
            if stime >= t
                # Cache with RUN_ETIME closest to this stime
                et = t
                break
            end
        end

        if not @caches.has_key?(et)
            cache = OpenNebulaSensorCache.new()
            cache.load(@cache_prefix + et.to_s())
            @caches[et] = cache
        end
        return @caches[et]
    end


    def store(cache)
        cache.store(@cache_prefix + cache.etime.to_s())
        @caches[cache.etime] = cache
    end

end #OpenNebulaSensorCacheManager


class OpenNebulaVirtualMachine

    attr_reader :info

    # States from which VM can never transition to a different state
    COMPLETED_STATES = Set.new("6")

    # OpenNebula will return the information in form of a hash
    # To extract relevant information, just create an entry in the fields_map
    # with the key as the attribute name you want and value as array keys that
    # lead to the info

    FIELDS_MAP = {
        "ID"              => ["ID"],
        "NAME"            => ["NAME"],
        "STIME"           => ["STIME"],
        "ETIME"           => ["ETIME"],
        "STATE"           => ["STATE"],
        "LCM_STATE"       => ["LCM_STATE"],
        "MEMORY"          => ["MEMORY"],
        "CPU"             => ["CPU"],
        "VCPU"            => ["TEMPLATE", "VCPU"],
        "MEMORY_REQ(MB)"  => ["TEMPLATE", "MEMORY"],
        "HID"             => ["HISTORY_RECORDS", "HISTORY", "HID"],
        "HISTORY_STIME"   => ["HISTORY_RECORDS", "HISTORY", "STIME"],
        "HISTORY_ETIME"   => ["HISTORY_RECORDS", "HISTORY", "ETIME"],
        "HISTORY_REASON"  => ["HISTORY_RECORDS", "HISTORY", "REASON"],
        "HOSTNAME"        => ["HISTORY_RECORDS", "HISTORY", "HOSTNAME"],
        "MAC"             => ["TEMPLATE", "NIC", "MAC"],
        "IP"              => ["TEMPLATE", "NIC", "IP"],
        "NETWORK"         => ["TEMPLATE", "NIC", "NETWORK"],
        "NETWORK_ID"      => ["TEMPLATE", "NIC", "NETWORK_ID"],
        "DISK_ID"         => ["TEMPLATE", "DISK", "DISK_ID"],
        "DISK_TYPE"       => ["TEMPLATE", "DISK", "TYPE"],
        "DISK_SIZE"       => ["TEMPLATE", "DISK", "SIZE"],
        "DISK_IMAGE"      => ["TEMPLATE", "DISK", "IMAGE"],
        "DISK_IMAGE_ID"   => ["TEMPLATE", "DISK", "IMAGE_ID"],
        "UID"             => ["UID"],
        "USERNAME"        => ["UNAME"],
        "GID"             => ["GID"],
        "GNAME"           => ["GNAME"],
    }

    # Class constructor
    def initialize(info={})
        @info = info
    end

    # Class constructor
    # Get the info from the OpenNebula VirtualMachine class
    def initialize(client, id)
        @info = {}
        vm = VirtualMachine.new_with_id(id, client)
        vm.info()
        @info = vm.to_hash()["VM"]
        if @info.size() == 1
            return
        end

        FIELDS_MAP.each_key() do |field|
            @info[field] = extract_field_values(@info, FIELDS_MAP[field])
        end
        # Additional info that cannot be mapped
        @info["STATE_STR"] = vm.state_str()
        @info["LCM_STATE_STR"] = vm.lcm_state_str()
        #puts @info.inspect()
    end


    def is_completed()
        if (@info.size() > 1) and (@info.has_key?("STATE"))
            return COMPLETED_STATES.include?(@info["STATE"])
        end

        return false
    end

    
    def guessed_etime()
        etime = 0
        if @info.has_key?("HISTORY_ETIME") and @info["HISTORY_ETIME"]
            if (@info["HISTORY_ETIME"]).kind_of?(Array)
                etime = Integer(@info["HISTORY_ETIME"][@info["HISTORY_ETIME"].size()-1])
            else
                etime = Integer(@info["HISTORY_ETIME"])
            end
        else
            etime = Integer(@info["ETIME"])
        end
        return etime
    end
    
    def guessed_stime()
        stime = 0
        if @info.has_key?("HISTORY_STIME") and @info["HISTORY_STIME"]
            if @info["HISTORY_STIME"].kind_of?(Array)
                stime = Integer(@info["HISTORY_STIME"][0])
            else
                stime = Integer(@info["HISTORY_STIME"])
            end
            if stime > Integer(@info["STIME"])
                stime = Integer(@info["STIME"])
            end
        else
            stime = Integer(@info["STIME"])
        end
    
        return stime
    end


    def predates_era(time)
        etime = guessed_etime()
        if time > 0
            #puts @info["ID"] +":"+ Integer(@info["ETIME"]).to_s + "=========>"
            #puts "predates_era: #{@info["ID"]} : #{time} : #{etime} : #{is_completed()}"
            if is_completed() and etime > 0 and etime < time
                # Compare it with the last etime in the history. Thats the only
                # correct means to make sure the vm was not done before
                return true
            end
        end
        return false
    end

    
    def postdates_era(time)
        stime = guessed_stime()
        if time > 0
            # Usually we want to consider @info["STIME"]. When the vm is 
            # resubmitted, the STIME is overwritten by STIME when resubmitted
            # In this case first value in @info["HISTORY_STIME"] is best info
            #puts "postdates_era: #{@info["ID"]} : #{time} : #{stime}"
            if stime > time and stime > 0
                return true
            end
        end
    
        return false
    end

    
    def lived_in_era(stime, etime)
        #if (stime > 0) and (etime > 0) and
        #(Integer(vm["STIME"]) >= stime) and (vm_predates_era(vm, etime))

        # VM launched and shutdown in the interval
        if (stime > 0) and (etime > 0) and
           (not postdates_era(stime)) and (predates_era(etime))
            return true
        end
        return false
    end


    def extract_field_values(info, fields)
        if info.is_a?(Hash)
            if info.has_key?(fields[0])
                if fields.size() == 1
                    return info[fields[0]]
                else
                    return extract_field_values(info[fields[0]],
                                                fields.slice(1,fields.size()-1))
                end
            else
                return nil
            end
        elsif info.is_a?(Array) 
            ret_arr = []
            info.each() do |i|
                ret_arr.push(extract_field_values(i, fields))
            end
            return ret_arr
        else
            return nil
        end
    end


end #OpenNebulaVirtualMachine
##############################################################################
# Custom Functions
##############################################################################

def output_results(results, file)
    outfile = File.new(file, "w")
    old = $stdout
    $stdout = outfile
    puts results
    outfile.close()
    $stdout = old
end


def get_queued_vm_ids(vms, etime)
    ids = []
    vms.each_key() do |id|
        if (vms[id].guessed_etime() > etime) or (not vms[id].is_completed())
            ids << id
        end
    end
    ids.sort!
    return ids
end

##############################################################################
# Main
##############################################################################

#CREDENTIALS = nil
#ENDPOINT = "http://fermicloud319.fnal.gov:2633/RPC2"
#HASH = true
#client = Client.new(CREDENTIALS, ENDPOINT, HASH)

###############################################################################
# Command line parsing
###############################################################################
options = {}
optparse = OptionParser.new() do |opts|
    opts.banner = "Usage: blah blah blah ..."

    options[:time] = Time.now().to_i()
    opts.on('-t', '--time TIME', 'Sec since epoch') do |t|
        options[:time] = Integer(t)
    end

    options[:delta] = -3600
    opts.on('-d', '--delta DELTA', 'Sec since time. Defaults to -3600') do |d|
        options[:delta] = Integer(d)
    end
    
    options[:all] = false
    opts.on('-a', '--all', 'Query all the vms. Ignore time & delta') do |a|
        options[:all] = true
    end
    
    options[:cachedir] = "/var/tmp/one-gratia-history"
    opts.on('-c', '--cache-dir CACHEDIR', 'Cache dir. Defaults to /var/tmp/onestats') do |cachedir|
        options[:cachedir] = cachedir
    end
    
    options[:output] = nil
    opts.on('-o', '--output OUTPUT', 'File to store VM information. Defaults to /var/tmp/one-gratia-history/onestats') do |o|
        options[:output] = o
    end
    
    opts.on( '-h', '--help', 'Display help screen' ) do
        puts opts
        exit
    end
end
    
# Parse the command-line. There are two forms of the parse method.
# The 'parse' method simply parses ARGV, while the 'parse!' method parses
# ARGV and removes any options found there, as well as any parameters for
# the options. What's left is the list of files to resize.
optparse.parse!

###############################################################################

stime = etime = nil

if options[:delta] < 0
    stime = options[:time] + options[:delta]
    etime = options[:time]
else
    stime = options[:time]
    etime = options[:time] + options[:delta]
end

# Use the default, i.e. anything that comes from the configs
client = Client.new()


if not File.directory?(options[:cachedir])
    Dir.mkdir(options[:cachedir])
end

outputfile = nil
if options[:output]
    outputfile = options[:output]
else
    outputfile = File.join(options[:cachedir], "/onestats")
end

#cachefile = File.join(options[:cachedir], "/cache")

last_run_etime = 0
id = 1
vms = {}

cache_manager = OpenNebulaSensorCacheManager.new(cachedir=options[:cachedir])
cache = nil

if not options[:all] 
    # Check if the cache from last run exists.
    # Cache has list of running VMs since last run and the last known ID
    cache = cache_manager.find(stime)

    if cache.is_valid
        # Get the info for vms that we know were running in last run
        cache.queued_vm_ids.each do |i|
            #puts "Last known ids: #{i}"
            vm = OpenNebulaVirtualMachine.new(client, i)
            if (vm.info.size() > 2) and 
               (not vm.predates_era(stime)) and
               (not vm.postdates_era(etime))
                vms[i] = vm
            end
        end
    
        # Start looking for VMs after the last known id
        id = cache.last_known_id + 1
    else
        puts "Ignoring Cache"
    end
end

# Check for any vms past last known vm id that may have state transitions
# This is required so we consider any vms that may have been launched and
# shutdown since last known run

while 1
    vm = OpenNebulaVirtualMachine.new(client, id)
    if (vm.info.size() < 2) or vm.postdates_era(etime)
        # We hit an empty vm_info (VM does not exist) or past the etime we care
        # No need to look for more vms
        break
    end
    #puts "While loop ids: #{id}"
    #puts vm.info.inspect()
    #puts vm.info.size()

    if options[:all]
        vms[id] = vm
    else
        # Consider the stime and etime. We only need vms that were running or
        # had a state transition in the interval stime - etime
        if not vm.predates_era(stime)
            vms[id] = vm
        end
    end

    id += 1
end

output_results(vms.inspect().gsub("=>", ": ").gsub("nil", "None"), outputfile)

result_cache = OpenNebulaSensorCache.new(rtime=Time.now().to_i(), 
                                         stime=stime, etime=etime, 
                                         last_known_id=(id-1),
                                         queued_vm_ids=get_queued_vm_ids(vms, etime))
cache_manager.store(result_cache)



###############################################################################
# Print Short Runtime Report to stdout
###############################################################################

cachefile = "None"
if cache and cache.filename
    cachefile = cache.filename
end

puts "________________________________________________________________________"
puts "                                 REPORT"
puts "________________________________________________________________________"
puts "Options: #{options.inspect()}"
if options[:all]
    puts "Reporting all vms: #{options[:all]}"
else
    puts "stime: #{stime}"
    puts "etime: #{etime}"
end
puts "Output: #{outputfile}"
puts "Cachefile Used: #{cachefile}"
puts "Cachefile Wrote: #{result_cache.filename}"
puts "VMs Found: #{vms.size()}"
puts "VM Ids: #{vms.keys().sort!.inspect()}"
puts "________________________________________________________________________"

exit 0
