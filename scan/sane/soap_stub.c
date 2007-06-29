/************************************************************************************\

  soap_stub.c 

  (c) 2006 Copyright Hewlett-Packard Development Company, LP

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

#include "sane.h"

SANE_Status soap_open(SANE_String_Const device, SANE_Handle *handle)
{
   return SANE_STATUS_INVAL;
}

void soap_close(SANE_Handle handle)
{
}

const SANE_Option_Descriptor * soap_get_option_descriptor(SANE_Handle handle, SANE_Int option)
{
   return 0;
}

SANE_Status soap_control_option(SANE_Handle handle, SANE_Int option, SANE_Action action, void *value, SANE_Int *set_result)
{
   return SANE_STATUS_INVAL;
}

SANE_Status soap_get_parameters(SANE_Handle handle, SANE_Parameters *params)
{
   return SANE_STATUS_GOOD;
}

SANE_Status soap_start(SANE_Handle handle)
{
   return SANE_STATUS_GOOD;
}

SANE_Status soap_read(SANE_Handle handle, SANE_Byte *data, SANE_Int maxLength, SANE_Int *length)
{
   return SANE_STATUS_GOOD;
}

void soap_cancel(SANE_Handle handle)
{
}





