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
#include "hpmud.h"
#include "common.h"
#include "pml.h"
#include "io.h"

int __attribute__ ((visibility ("hidden"))) SendScanEvent( char * device_uri, int event, char * type )
{
#if 0
    char message[HPMUD_BUFFER_SIZE];

    int len = sprintf( message, "msg=Event\ndevice-uri=%s\nevent-code=%d\nevent-type=%s\n", 
        device_uri, event, type );

    if (send(hplip_session->hpssd_socket, message, len, 0) == -1) 
    {
       bug("SendScanEvent(): unable to send message: %m\n" );  
    }
#endif
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

