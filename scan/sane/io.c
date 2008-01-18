/************************************************************************************\

  io.c - HP SANE backend for multi-function peripherals (libsane-hpaio)

  (c) 2001-2007 Copyright Hewlett-Packard Development Company, LP

  Permission is hereby granted, free of charge, to any person obtaining a copy 
  of this software and associated documentation files (the "Software"), to deal 
  in the Software without restriction, including without limitation the rights 
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
  of the Software, and to permit persons to whom the Software is furnished to do 
  so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS 
  FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
  IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

  Contributing Authors: Don Welch, David Suffield 

\************************************************************************************/

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include "hpmud.h"
#include "common.h"
#include "pml.h"
#include "io.h"

int __attribute__ ((visibility ("hidden"))) SendScanEvent(char *device_uri, int event, char *type)
{
   struct sockaddr_in pin;  
   char message[512];  
   int len=0;
   int hpssd_socket=-1, hpssd_port_num=2207;

   bzero(&pin, sizeof(pin));  
   pin.sin_family = AF_INET;  
   pin.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
   pin.sin_port = htons(hpssd_port_num);  
    
   if ((hpssd_socket = socket(AF_INET, SOCK_STREAM, 0)) == -1) 
   {  
      BUG("unable to create hpssd socket %d: %m\n", hpssd_port_num);
      goto bugout;  
   }  

   if (connect(hpssd_socket, (void *)&pin, sizeof(pin)) == -1)  
   {  
      BUG("unable to connect hpssd socket %d: %m\n", hpssd_port_num);
      goto bugout;  
   }  

   len = sprintf(message, "msg=Event\ndevice-uri=%s\nevent-code=%d\nevent-type=%s\n", device_uri, event, type);
 
   /* Send message with no response. */
   if (send(hpssd_socket, message, len, 0) == -1) 
   {  
      BUG("unable to send Event %s %d: %m\n", device_uri, event);
   }  

bugout:
   if (hpssd_socket >= 0)
      close(hpssd_socket);

    return 0;    
}

/* Read full requested data length in BUFFER_SIZE chunks. Return number of bytes read. */
int __attribute__ ((visibility ("hidden"))) ReadChannelEx(int deviceid, int channelid, unsigned char * buffer, int length, int timeout)
{
   int n, len, size, total=0;
   enum HPMUD_RESULT stat;

   size = length;

   while(size > 0)
   {
      len = size > HPMUD_BUFFER_SIZE ? HPMUD_BUFFER_SIZE : size;
        
      stat = hpmud_read_channel(deviceid, channelid, buffer+total, len, timeout, &n);
      if (n <= 0)
      {
         break;    /* error or timeout */
      }
      size-=n;
      total+=n;
   }
        
   return total;
}

