/*****************************************************************************\
  pscript.h : Interface for the PScript class

  Copyright (c) 1996 - 2001, Hewlett-Packard Co.
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


#ifndef APDK_PSCRIPT_H
#define APDK_PSCRIPT_H

APDK_BEGIN_NAMESPACE

#ifdef  APDK_HIGH_RES_MODES
#define PS_BASE_RES 300
#else
#define PS_BASE_RES 150
#endif


typedef struct _StrList
{
	char *pPSString;
	struct _StrList *next;
} StrList;

/*!
\internal
*/
class PScript : public Printer
{
public:
    PScript (SystemServices* pSS,int numfonts=0, BOOL proto=FALSE);
	~PScript ();

    PrintMode* GetMode (int index);

    virtual Header* SelectHeader (PrintContext* pc);
    virtual DRIVER_ERROR VerifyPenInfo ();
    virtual DRIVER_ERROR ParsePenInfo (PEN_TYPE& ePen, BOOL QueryPrinter=TRUE);
    virtual DISPLAY_STATUS ParseError (BYTE status_reg);
    virtual DRIVER_ERROR Encapsulate (const RASTERDATA* InputRaster, BOOL bLastPlane);
	inline virtual BOOL SupportSeparateBlack (PrintMode *pCurrentMode) {return FALSE;}
	virtual DRIVER_ERROR Flush (int FlushSize)
	{
		return NO_ERROR;
	}

	virtual int PrinterLanguage ()
	{
		return 10;	// PostScript
	}

	virtual DRIVER_ERROR SaveText (const char *psStr, int iPointSize, int iX, int iY,
								   const char *pTextString, int iTextStringLen,
								   BOOL bUnderline);

    virtual BOOL UseCMYK(unsigned int iPrintMode) { return FALSE;}

    Compressor* CreateCompressor (unsigned int RasterSize);
	DRIVER_ERROR SendText (int iCurYPos);
	void FreeList ();
	int		m_pCurResolution;
protected:

#ifdef APDK_HP_UX
    virtual PScript & operator = (Printer& rhs)
    {
        return *this;
    }
#endif

	StrList	*m_pHeadPtr;
	StrList	*m_pCurItem;
}; // PScript

class PScriptDraftMode : public PrintMode
{
public:
	PScriptDraftMode ();
};	// PScriptDraftMode

class PScriptNormalMode : public PrintMode
{
public:
    PScriptNormalMode ();
}; // PScriptNormalMode

class PScriptGrayMode : public PrintMode
{
public:
	PScriptGrayMode ();
}; // PScriptGrayMode

class ModePS0 : public Compressor
{
public:
    ModePS0 (SystemServices* pSys,unsigned int RasterSize);
    virtual ~ModePS0 ();
    BOOL Process (RASTERDATA* input);
}; //Mode2

#ifdef APDK_PSCRIPT
//! PScriptProxy
/*!
******************************************************************************/
class PScriptProxy : public PrinterProxy
{
public:
    PScriptProxy() : PrinterProxy(
        "PostScript",                   // family name
        "postscript\0"                  // models
#ifdef APDK_MLC_PRINTER
#endif
    ) {m_iPrinterType = ePScript;}
    inline Printer* CreatePrinter(SystemServices* pSS) const { return new PScript(pSS); }
	inline PRINTER_TYPE GetPrinterType() const { return ePScript;}
	inline unsigned int GetModelBit() const { return 0x10;}
};
#endif

APDK_END_NAMESPACE

#endif //APDK_PSCRIPT_H
