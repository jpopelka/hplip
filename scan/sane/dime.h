/************************************************************************************\

  dime.h - Direct Internet Message Encapsulation (DIME) data consumer

  (c) 2008 Copyright Hewlett-Packard Development Company, LP

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

\************************************************************************************/

#ifndef _DIME_H
#define _DIME_H

enum DIME_RESULT
{
   DIME_R_OK = 0,
   DIME_R_IO_ERROR,
   DIME_R_EOF,
   DIME_R_IO_TIMEOUT,
   DIME_R_MALLOC_ERROR,
   DIME_R_INVALID_BUF_SIZE,
};

typedef void * DIME_HANDLE;

enum DIME_RESULT __attribute__ ((visibility ("hidden"))) dime_open(HTTP_HANDLE http_handle, DIME_HANDLE *handle);
enum DIME_RESULT __attribute__ ((visibility ("hidden"))) dime_close(DIME_HANDLE handle);
enum DIME_RESULT __attribute__ ((visibility ("hidden"))) dime_read(DIME_HANDLE handle, void *data, int max_size, int sec_timout, int *bytes_read);

#endif  // _DIME_H


