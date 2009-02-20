/*****************************************************************************\
  ljzjscolor.cpp : Implementation for the LJZjsColor class

  Copyright (c) 1996 - 2006, Hewlett-Packard Co.
  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:
  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.
  3. Neither the name of Hewlett-Packard nor the names of its
     contributors may be used to endorse or promote products derived
     from this software without specific prior written permission.

  THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR IMPLIED
  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
  NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
  TO, PATENT INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
\*****************************************************************************/


#ifdef APDK_LJZJS_COLOR

#include "header.h"
#include "io_defs.h"
#include "printerproxy.h"
#include "resources.h"
#include "ljzjs.h"
#include "ljzjscolor.h"

APDK_BEGIN_NAMESPACE

extern uint32_t ulMapGRAY_K_6x6x1[9 * 9 * 9];

extern uint32_t ulMapDJ600_CCM_K[9 * 9 * 9];
extern uint32_t ulMapDJ970_KCMY[9 * 9 * 9];
extern unsigned char ucMapDJ4100_KCMY_Photo_BestA_12x12x1[];
extern unsigned char ucMapDJ4100_KCMY_Photo_BestV_12x12x1[];
extern unsigned char ucMapDJ4100_KCMY_BestA_12x12x1[];
extern unsigned char ucMapDJ4100_KCMY_BestS_12x12x1[];
extern BYTE *GetHT12x12x1_4100_Photo_Best ();

LJZjsColor::LJZjsColor (SystemServices* pSS, int numfonts, BOOL proto)
    : LJZjs (pSS, numfonts, proto)
{

	ePen = BOTH_PENS;

    pMode[GRAYMODE_INDEX]    = new LJZjsColorDraftGrayMode ();
    pMode[DEFAULTMODE_INDEX] = new LJZjsColorNormalGrayMode ();
    pMode[SPECIALMODE_INDEX] = new LJZjsColorDraftColorMode ();
    pMode[SPECIALMODE_INDEX+1] = new LJZjsColorNormalColorMode ();
    ModeCount = 4;

    CMYMap = NULL;
#ifdef  APDK_AUTODUPLEX
    m_bRotateBackPage = FALSE;  // Lasers don't require back side image to be rotated
#endif
    m_pszInputRasterData = NULL;
    m_dwCurrentRaster = 0;
    m_cmColorMode = GREY_K;
    m_bStartPageSent = FALSE;
    m_iPlaneNumber = 0;
    m_iBPP = 2;  // Setting this to 1 will cause problems
    for (int i = 1; i < 4; i++)
    {
        m_iP[i] = i - 1; //{3, 0, 1, 2};
    }
    m_iP[0] = 3;
    m_bIamColor = TRUE;
    m_iPrinterType = eLJZjsColor;
}

LJZjsColor::~LJZjsColor ()
{
}

/*
 *  Draft
 *  Gray
 */
LJZjsColorDraftGrayMode::LJZjsColorDraftGrayMode ()
: GrayMode(/*ulMapDJ600_CCM_K*/ulMapGRAY_K_6x6x1)
{

    ResolutionX[0] =
    ResolutionY[0] = 600;
    BaseResX =
    BaseResY = 600;
    MixedRes = FALSE;
    bFontCapable = FALSE;
    theQuality = qualityDraft;
    pmQuality = QUALITY_DRAFT;
#ifdef APDK_AUTODUPLEX
    bDuplexCapable = TRUE;
#endif
    Config.bCompress = FALSE;
}

/*
 * Normal
 * Gray
 */
LJZjsColorNormalGrayMode::LJZjsColorNormalGrayMode ()
: GrayMode(/*ulMapDJ600_CCM_K*/ulMapGRAY_K_6x6x1)
{

    ResolutionX[0] =
    ResolutionY[0] = 600;
    BaseResX =
    BaseResY = 600;
	TextRes  = 600;
    MixedRes = FALSE;
    bFontCapable = FALSE;
#ifdef APDK_AUTODUPLEX
    bDuplexCapable = TRUE;
#endif
    Config.bCompress = FALSE;
}

/*
 * Draft
 * Color
 */
LJZjsColorDraftColorMode::LJZjsColorDraftColorMode ()
: PrintMode(ulMapDJ970_KCMY)
{
	cmap.ulMap1 =
	cmap.ulMap2 = NULL;
	cmap.ulMap3 = (unsigned char *) ucMapDJ4100_KCMY_Photo_BestA_12x12x1;
	ColorFEDTable = GetHT12x12x1_4100_Photo_Best ();

    ResolutionX[0] = ResolutionY[0] = 600;
    BaseResX = BaseResY = 600;
    TextRes = 600;
    MixedRes = FALSE;
    bFontCapable = FALSE;
    pmQuality = QUALITY_DRAFT;
    theQuality = qualityDraft;
#ifdef APDK_AUTODUPLEX
    bDuplexCapable = TRUE;
#endif
    Config.bCompress = FALSE;
}


/*
 * Normal
 * Color
 */
LJZjsColorNormalColorMode::LJZjsColorNormalColorMode ()
: PrintMode(ulMapDJ970_KCMY)
{
	cmap.ulMap1 =
	cmap.ulMap2 = NULL;
	cmap.ulMap3 = (unsigned char *) ucMapDJ4100_KCMY_Photo_BestA_12x12x1;
    
	ColorFEDTable = GetHT12x12x1_4100_Photo_Best ();

    for (int i = 0; i < 4; i++)
    {
        ColorDepth[i] = 1;

        ResolutionX[i] = 600;
        ResolutionY[i] = 600;
    }
//    ColorDepth[0] = 1;
    ResolutionX[0] =
    ResolutionY[0] = 600;
    BaseResX       =
    BaseResY       = 600;
    TextRes        = 600;
    MixedRes = FALSE;
    bFontCapable = FALSE;
    pmQuality = QUALITY_NORMAL;
#ifdef APDK_AUTODUPLEX
    bDuplexCapable = TRUE;
#endif
    Config.bCompress = FALSE;
}

DRIVER_ERROR LJZjsColor::Encapsulate (const RASTERDATA *pRasterData, BOOL bLastPlane)
{
    if( m_cmColorMode == COLOR )
    {
        if (pRasterData != NULL)
        {
            BYTE	*p = m_pszCurPtr + (m_iP[m_iPlaneNumber] * m_dwWidth * m_iBPP) * m_dwLastRaster;
            for (int i = 0; i < pRasterData->rastersize[COLORTYPE_COLOR]; i++)
            {
                p[i*m_iBPP] = szByte1[pRasterData->rasterdata[COLORTYPE_COLOR][i]];
                p[i*m_iBPP+1] = szByte2[pRasterData->rasterdata[COLORTYPE_COLOR][i]];
                p[i*m_iBPP] |= (p[i*m_iBPP] >> 1);
                p[i*m_iBPP+1] |= (p[i*m_iBPP+1] >> 1);
            }
        }
        m_iPlaneNumber++;

        if (bLastPlane)
        {
            m_dwCurrentRaster++;
            m_pszCurPtr += m_iBPP * m_dwWidth;
            m_iPlaneNumber = 0;
        }
        
    }
    else
    {
        if (pRasterData != NULL)
        {
            for (int i = 0; i < pRasterData->rastersize[COLORTYPE_COLOR]; i++)
            {
                m_pszCurPtr[i*m_iBPP]   = szByte1[pRasterData->rasterdata[COLORTYPE_COLOR][i]];
                m_pszCurPtr[i*m_iBPP+1] = szByte2[pRasterData->rasterdata[COLORTYPE_COLOR][i]];
                m_pszCurPtr[i*m_iBPP]   |= (m_pszCurPtr[i*m_iBPP] >> 1);
                m_pszCurPtr[i*m_iBPP+1] |= (m_pszCurPtr[i*m_iBPP+1] >> 1);
            }
        }
        
        m_dwCurrentRaster++;
        m_pszCurPtr += (m_iBPP * m_dwWidth);
    }

    if (m_dwCurrentRaster == m_dwLastRaster)
    {
        JbigCompress ();
    }
    return NO_ERROR;
}

DRIVER_ERROR LJZjsColor::EndPage ()
{
    DRIVER_ERROR        err = NO_ERROR;
    BYTE                szStr[256];
    int                 i = 0;
    int                 iCol = (m_cmColorMode == COLOR) ? 1 : 0;

    i = SendChunkHeader (szStr, 112, ZJT_END_PAGE, 8);
    for (int j = 0; j < 8; j++)
    {
        i += SendItem (szStr+i, ZJIT_UINT32, 0x8200+j, (j % 4 == 3) ? 1 : iCol);
    }
    err = Send ((const BYTE *) szStr, 112);

    m_bStartPageSent = FALSE;

    m_dwCurrentRaster = 0;
    m_pszCurPtr = m_pszInputRasterData;

    return err;
}

DRIVER_ERROR LJZjsColor::SendPlaneData (int iPlaneNumber, HPLJZjsJbgEncSt *se, HPLJZjcBuff *pcBuff, BOOL bLastStride)
{
    DRIVER_ERROR        err = NO_ERROR;
    BYTE                szStr[256];
    static    BOOL      bNotSent = TRUE;
    int                 kEnd = (m_cmColorMode == COLOR) ? 5 : 2;
    int                 i = 0;

    /*
     *  Send JBIG header info
     */

    // Send out the JBIG header if first plane and it hasn't already been sent out yet.
    if (iPlaneNumber == 1 && bNotSent)
    {
        bNotSent = FALSE;
        i = 0;
        for (int k = 1; k < kEnd; k++)
        {
            i = SendChunkHeader (szStr, 132, ZJT_BITMAP, 8);
            szStr[13] += 20;
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_BITMAP_TYPE, 1);
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_BITMAP_PIXELS, se->xd);
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_BITMAP_STRIDE, se->xd);
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_BITMAP_LINES, se->yd);
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_BITMAP_BPP, 1);
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_VIDEO_BPP, m_iBPP);
            i += SendItem (szStr+i, ZJIT_UINT32, ZJI_PLANE, 
                           (m_cmColorMode == COLOR) ? k : 4);
            i += SendItem (szStr+i, ZJIT_BYTELUT, ZJI_ENCODING_DATA, 20, 20);
            szStr[i++] = se->dl;
            szStr[i++] = se->d;
            szStr[i++] = se->planes;
            szStr[i++] = 0;
            for (int j = 3; j >= 0; j--)
            {
                szStr[i] = (BYTE) ((se->xd  >> (8 * j)) & 0xFF);
                szStr[4+i] = (BYTE) ((se->yd  >> (8 * j)) & 0xFF);
                szStr[8+i] = (BYTE) ((se->l0  >> (8 * j)) & 0xFF);
                i++;
            }
            i += 8;

            szStr[i++] = se->mx;
            szStr[i++] = se->my;
            szStr[i++] = se->order;
            szStr[i++] = se->options;
            err = Send ((const BYTE *) szStr, 132);
            ERRCHECK;
        }
    }

    BYTE    *p = pcBuff->pszCompressedData + 20;
    int     dwNumItems;
    int     dwSize;

    pcBuff->dwTotalSize -= 20;
    int     iPadCount = 0;

    i = 0;
    if (pcBuff->dwTotalSize % 4)
    {
        iPadCount = ((pcBuff->dwTotalSize / 4 + 1) * 4) - pcBuff->dwTotalSize;
    }

    dwSize = 16 + pcBuff->dwTotalSize + iPadCount;
    dwNumItems = 1;
    if (bLastStride)
    {
        dwNumItems = 3;
        bNotSent = TRUE;
    }
    dwSize += (dwNumItems * 12);
    i = SendChunkHeader (szStr, dwSize, ZJT_BITMAP, dwNumItems);
    i += SendItem (szStr+i, ZJIT_UINT32, ZJI_PLANE, (kEnd == 5) ? iPlaneNumber : 4);
    if (bLastStride)
    {
        i += SendItem (szStr+i, ZJIT_UINT32, ZJI_BITMAP_LINES, se->yd);
        i += SendItem (szStr+i, ZJIT_UINT32, ZJI_END_PLANE, bLastStride);
    }
    err = Send ((const BYTE *) szStr, i);
    ERRCHECK;
        
    err = Send ((const BYTE *) p, pcBuff->dwTotalSize);
    ERRCHECK;
    if (iPadCount != 0)
    {
        memset (szStr, 0, iPadCount);
        err = Send ((const BYTE *) szStr, iPadCount);
    }

    return err;
}

DRIVER_ERROR LJZjsColor::VerifyPenInfo()
{
    ePen = BOTH_PENS;
    return NO_ERROR;
}

DRIVER_ERROR LJZjsColor::ParsePenInfo (PEN_TYPE& ePen, BOOL QueryPrinter)
{
    ePen = BOTH_PENS;

    return NO_ERROR;
}

APDK_END_NAMESPACE

#endif  // defined APDK_LJZJS_COLOR
