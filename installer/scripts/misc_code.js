<!--
/*
 (c) Copyright 2001-2007 Hewlett-Packard Development Company, L.P.

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

 Author: Pete Parks

*/
-->



/*
Credit: Mike Hall of www.BrainJar.com
Site: http://www.codingforums.com/showthread.php?s=&threadid=14463
Posted: 02-11-2003, 03:16 PM
Code:  The code below is derived from a post Mike made on "codingforums". 
Copyright: http://www.brainjar.com/terms.asp
*/

//////////////////////////////////////////////////////
// XmlLoader Class
//////////////////////////////////////////////////////

// Set properties.


function createXmlLoader()
{
    var ajaxObject = null;

    var MSXML_IMPLEMENTATION_IDS = new Array(
    "MSXML2.XMLHTTP.4.0",
    "MSXML2.XMLHTTP.3.0",
    "MSXML2.XMLHTTP",
    "Microsoft.XMLHTTP"
    );

    // Create the appropriate XMLHTTP object for the browser.
    // For Netscape Mozilla:
    if (window.XMLHttpRequest != null)
    {
        ajaxObject = new XMLHttpRequest();
        // For MS Internet Exploder:
    } else if (window.ActiveXObject != null) {
        // Try each Implementation ID until one works.
        var success = false;
        for (var i = 0; i < MSXML_IMPLEMENTATION_IDS.length && !success; i++)
        {
            try
            {
                success = true;
            }
            catch (e) 
            {
                throw "We didn't get a valid Microsoft XML object.";
            }
        }

        if (!success)  // If it couldn't be created, throw an exception.
        {  
            throw "Cannot create an XMLHTTP object.";
        }
    }
    return ajaxObject;
    
};

//
// Implementation of the XmlLoader.addServerArguement() method.
//
function addLoaderArguements(name, value)
{
    // Add the name/value pair to the request data.
    if (data.length > 0)
    {
        data += "&";
    }
    data += window.escape(name) + "=" + window.escape(value);
    operation = "?";    
};

//
// Implementation of the XmlLoader.initializeRequest() method.
//
function setLoaderRequestOptions(ajaxObject, path, data, operation, requestOperation, synchronization)
{
    ajaxObject.open(requestOperation, path + operation + data, synchronization);
    ajaxObject.setRequestHeader("Content-Type", "text/xml");
    ajaxObject.send("");
};

//
// Implementation of the XmlLoader.XmlLoaderHandleResponse() method.
//
function setXmlLoaderHandleResponse(ajaxObject) 
{
    // only if req shows "loaded"
    if (ajaxObject.readyState == 4) {
        // only if "OK"
        if (ajaxObject.status == 200) {
            // ...processing statements go here...
            var text = ajaxObject.responseText
            setProgressElementText(text);
        } else {
            // "There was a problem retrieving the XML data:" + req.status
        }
    }
};

//
// Implementation of the XmlLoader.submit() method.
//
function submitXmlLoaderRequest(ajaxObject, requestOperation, path, synchronization)
{
    var info = "";
    var data = "";
    var operation = "";
    if(ajaxObject == null) {
        ajaxObject = createXmlLoader();
    }
    
    try
    {
        // Set up a synchronous GET request, set the data encoding header and send it.
        if (synchronization) {  // Specify the function that will handle the HTTP response
            ajaxObject.onreadystatechange  = function()
            {
                setXmlLoaderHandleResponse(ajaxObject);
            }
            
        }
 
        setLoaderRequestOptions(ajaxObject, path, data, operation, requestOperation, synchronization);
        
        if(!synchronization) { 
            
            // Check the HTTP response status code. If it is not "OK," throw an exception.
            if (ajaxObject.status != 200) {
                info = "HTTP request for \"" + path + "\" failed with status \"" + ajaxObject.status + " " + ajaxObject.statusText + "\"";
                
            // Otherwise, return the response data as a text string.
            } else {
                info = ajaxObject.responseText;
            }
        }
    }
    catch (e)
    {
        throw "XmlLoader had an error: " + e;
    }
    return info;
};


/*
Credit: Peter-Paul Koch
Site: http://www.quirksmode.org/js/detect.html
Copyright: http://www.quirksmode.org/about/copyright.html
Code:  Browser detect
*/


function isKonquerorBase() {
    return (BrowserDetect.browser == 'Konqueror') ? 1 : 0;
}

function isFireFoxBase() {
    return (BrowserDetect.browser == 'Firefox') ? 1 : 0;
}

function isSafariBase() {
    return (BrowserDetect.browser == 'Safari') ? 1 : 0;
}

function isGaleonBased() {
    return (BrowserDetect.browser == 'Galeon') ? 1 : 0;
}


var BrowserDetect = {
    init: function () {
        this.browser = this.searchString(this.dataBrowser) || "An unknown browser";
        this.version = this.searchVersion(navigator.userAgent)
            || this.searchVersion(navigator.appVersion)
            || "an unknown version";
        this.OS = this.searchString(this.dataOS) || "an unknown OS";
    },
    searchString: function (data) {
        for (var i=0;i<data.length;i++) {
            var dataString = data[i].string;
            var dataProp = data[i].prop;
            this.versionSearchString = data[i].versionSearch || data[i].identity;
            if (dataString) {
                if (dataString.indexOf(data[i].subString) != -1)
                    return data[i].identity;
            }
            else if (dataProp)
                return data[i].identity;
        }
    },
    searchVersion: function (dataString) {
        var index = dataString.indexOf(this.versionSearchString);
        if (index == -1) return;
        return parseFloat(dataString.substring(index+this.versionSearchString.length+1));
    },
    dataBrowser: [
        {   string: navigator.userAgent,
            subString: "OmniWeb",
            versionSearch: "OmniWeb/",
            identity: "OmniWeb"
        },
        {
            string: navigator.vendor,
            subString: "Apple",
            identity: "Safari"
        },
        {
            prop: window.opera,
            identity: "Opera"
        },
        {
            string: navigator.vendor,
            subString: "iCab",
            identity: "iCab"
        },
        {
            string: navigator.vendor,
            subString: "KDE",
            identity: "Konqueror"
        },
        {
            string: navigator.userAgent,
            subString: "Firefox",
            identity: "Firefox"
        },
        {
            string: navigator.vendor,
            subString: "Camino",
            identity: "Camino"
        },
        {       // for newer Netscapes (6+)
            string: navigator.userAgent,
            subString: "Netscape",
            identity: "Netscape"
        },
        {
            string: navigator.userAgent,
            subString: "MSIE",
            identity: "Explorer",
            versionSearch: "MSIE"
        },
        {
            string: navigator.userAgent,
            subString: "Gecko",
            identity: "Mozilla",
            versionSearch: "rv"
        },
        {       // for older Netscapes (4-)
            string: navigator.userAgent,
            subString: "Mozilla",
            identity: "Netscape",
            versionSearch: "Mozilla"
        }
    ],
    dataOS : [
        {
            string: navigator.platform,
            subString: "Win",
            identity: "Windows"
        },
        {
            string: navigator.platform,
            subString: "Mac",
            identity: "Mac"
        },
        {
            string: navigator.platform,
            subString: "Linux",
            identity: "Linux"
        }
    ]

};
BrowserDetect.init();


/*
Credit: Mar 12, 2005 by lobo235

Site: http://www.netlobo.com/div_hiding.html
        
Code:  Showing and Hiding a DIV using CSS and Javascript

*/
function toggleLayer(doc, whichLayer)
{
    if (doc.getElementById) {
        // this is the way the standards work
        var style2 = doc.getElementById(whichLayer).style;
        style2.display = style2.display? "block":"none";
    } else if (doc.all) {
        // this is the way old msie versions work
        var style2 = doc.all[whichLayer].style;
        style2.display = style2.display? "":"block";
    } else if (doc.layers) {
        // this is the way nn4 works
        var style2 = doc.layers[whichLayer].style;
        style2.display = style2.display? "":"block";
    }
}

