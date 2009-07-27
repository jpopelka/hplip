/*****************************************************************************\
    hpimage.cpp : HP Image Saver

    Copyright (c) 2009, Hewlett-Packard Co.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:
    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.
    3. Neither the name of the Hewlett-Packard nor the names of its
       contributors may be used to endorse or promote products derived
       from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
    OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
    IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
    INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
    NOT LIMITED TO, PATENT INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
    HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
    STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
    IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
\*****************************************************************************/

#include <stdio.h>

#include "header.h"
#include "hpimage.h"

void HPImage::CreateBMPHeader (int width, int height, int planes, int bpp)
{
    memset (&this->bmfh, 0, 14);
    memset (&this->bmih, 0, 40);
    bmfh.bfOffBits = 54;
    bmfh.bfType = 0x4d42;
    bmfh.bfReserved1 = 0;
    bmfh.bfReserved2 = 0;
    bmih.biSize = DBITMAPINFOHEADER;
    bmih.biWidth = width;
    bmih.biHeight = -height;
    bmih.biPlanes = 1;
    bmih.biBitCount = planes * bpp;
    bmih.biCompression = 0;
    bmih.biSizeImage = width * height * planes * bpp / 8;
    bmih.biClrImportant = 0;
    bmih.biClrUsed = (planes == 3) ? 0 : 2;
    bmih.biXPelsPerMeter = 0;
    bmih.biYPelsPerMeter = 0;

    bmfh.bfSize = bmih.biSizeImage + bmfh.bfOffBits + bmih.biClrUsed * 4;
}

void HPImage::WriteBMPHeader (FILE *fp, int width, int height, eRasterType raster_type)
{
    if (fp == NULL)
    {
        return;
    }
    if (raster_type == BLACK_RASTER)
    {
        WriteKBMPHeader (fp, width, height);
    }
    else
    {
        WriteCBMPHeader (fp, width, height);
    }
}

void HPImage::WriteCBMPHeader (FILE *fp, int width, int height)
{
    if (fp == NULL)
        return;
    adj_c_width = width;
    if (width % 4)
    {
        adj_c_width = (width / 4 + 1) * 4;
    }
    color_raster = new BYTE[adj_c_width * 3];
    memset (color_raster, 0xFF, adj_c_width * 3);
    CreateBMPHeader(adj_c_width, height, 3, 8);
    fwrite (&this->bmfh.bfType, 1, sizeof (short), fp);
    fwrite (&this->bmfh.bfSize, 1, sizeof (int), fp);
    fwrite (&this->bmfh.bfReserved1, 1, sizeof (short), fp);
    fwrite (&this->bmfh.bfReserved2, 1, sizeof (short), fp);
    fwrite (&this->bmfh.bfOffBits, 1, sizeof (int), fp);
    fwrite (&this->bmih, 1, DBITMAPINFOHEADER, fp);
}

void HPImage::WriteKBMPHeader(FILE *fp, int width, int height)
{
    BYTE    cmap[8];
    if (fp == NULL)
        return;
    adj_k_width = width;
    if (width % 32)
    {
        adj_k_width = (width / 32 + 1) * 32;
    }
    CreateBMPHeader(adj_k_width, height, 1, 1);
    adj_k_width /= 8;
    black_raster = new BYTE[adj_k_width];
    memset (black_raster, 0, adj_k_width);

    fwrite (&this->bmfh.bfType, 1, sizeof (short), fp);
    fwrite (&this->bmfh.bfSize, 1, sizeof (int), fp);
    fwrite (&this->bmfh.bfReserved1, 1, sizeof (short), fp);
    fwrite (&this->bmfh.bfReserved2, 1, sizeof (short), fp);
    fwrite (&this->bmfh.bfOffBits, 1, sizeof (int), fp);
    fwrite (&this->bmih, 1, DBITMAPINFOHEADER, fp);
    memset(cmap, 0, sizeof(cmap));
    cmap[0] = cmap[1] = cmap[2] = cmap[3] = 255;
    fwrite(cmap, 1, sizeof(cmap), fp);
}

void HPImage::WriteBMPRaster (FILE *fp, BYTE *raster, int width, eRasterType raster_type)
{
    if (raster_type == BLACK_RASTER)
        return WriteKBMPRaster (fp, raster, width);
    else
        return WriteCBMPRaster (fp, raster, width);
}

void HPImage::WriteCBMPRaster (FILE *fp, BYTE *pbyrgb, int width)
{
    if (fp == NULL)
        return;
    //BYTE    c[3];
    int     i;
    BYTE    *p = pbyrgb;
    BYTE    *q = color_raster;
    if (pbyrgb == NULL)
    {
	memset (color_raster, 0xFF, adj_c_width * 3);
    }
    else
    {
        for (i = 0; i < width; i++) {
	    q[0] = p[2];
	    q[1] = p[1];
	    q[2] = p[0];
	    p += 3;
	    q += 3;
        }
    }
    fwrite (color_raster, 1, adj_c_width * 3, fp);
}

void HPImage::WriteKBMPRaster (FILE *fp, BYTE *pbyk, int width)
{
    if (fp == NULL)
        return;
    if (pbyk == NULL)
    {
        memset (black_raster, 0, adj_k_width);
    }
    else
    {
        memcpy (black_raster, pbyk, width);
    }
    fwrite (black_raster, 1, adj_k_width, fp);
}

HPImage::HPImage ()
{
    adj_c_width = 0;
    adj_k_width = 0;
    black_raster = NULL;
    color_raster = NULL;
}

HPImage::~HPImage ()
{
}

