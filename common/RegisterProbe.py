import Gratia
import httplib
import sys

if __name__ == '__main__':
        Gratia.Initialize()
        registrationhost = Gratia.Config.get_SSLRegistrationHost()
        registrationservice = Gratia.Config.get_SSLRegistrationService()
        probename = Gratia.Config.get_MeterName()
        #
        # if we are using ssl certs get them from the server
        #
        if Gratia.Config.get_UseGratiaCertificates() == 1:
                print "RequestingCert With: " + registrationhost + " Service: " + registrationservice
                connection = httplib.HTTPConnection(registrationhost)
                connection.connect()
                command = "command=request&arg1=" + probename
                connection.request("POST",registrationservice,command)
                response = connection.getresponse().read()
                args = response.split(":")
                cert = ""
                if args[0] == "error":
                        print "Error: ",args[1]
                        sys.exit
                else:
                        output = open(Gratia.Config.get_GratiaCertificateFile(),"w");
                        output.write(args[0]);
                        output.close();
                        output = open(Gratia.Config.get_GratiaKeyFile(),"w");
                        output.write(args[1]);
                        output.close();
                        print "Cert/Keyfile Saved"
                        cert = args[0]
        #
        # now - register something
        #
        if Gratia.Config.get_UseGratiaCertificates() == 1:
                print "Registering SSL Certs"
                command="command=register&arg1=" + probename + "&arg2=Probe&arg3=" + cert
                connection.request("POST",registrationservice,command)
                response = connection.getresponse().read()
                print response
                sys.exit
        else:
                print "Registering Fermi Certs"
                input = open(Gratia.Config.get_CertificateFile(),"r")
                pem = input.read()
                input.close()
                connection = httplib.HTTPConnection(registrationhost)
                connection.connect()
                command="command=register&arg1=" + probename + "&arg2=Probe&arg3=" + pem
                connection.request("POST",registrationservice,command)
                response = connection.getresponse().read()
                print response

        

