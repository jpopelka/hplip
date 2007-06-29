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


//////////////////////////////////////////////////////
// XmlLoader Class
//////////////////////////////////////////////////////
function XmlLoader(url)
{
    // Set properties.
    //alert("requested url" + url);
    this.url = url;
    this.data = "";
    this.operation = "";
    this.XmlLoaderObj = null;
    this.createLoader();
};

//
// Implementation of the XmlLoader.cleanup() method.
//
XmlLoader.prototype.cleanupLoader = function()
{
    // Reset the request data.
    this.data = "";
    this.url  = url;
    this.operation = "";
    this.XmlLoaderObj = null;
};
    
XmlLoader.prototype.createLoader = function ()
{

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
        this.XmlLoaderObj = new XMLHttpRequest();
        // For MS Internet Exploder:
    } else if (window.ActiveXObject != null) {
        // Try each Implementation ID until one works.
        var success = false;
        for (var i = 0; i < MSXML_IMPLEMENTATION_IDS.length && !success; i++)
        {
            try
            {
                this.XmlLoaderObj = new ActiveXObject(MSXML_IMPLEMENTATION_IDS[i]);
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
};

//
// Implementation of the XmlLoader.addServerArguement() method.
//
XmlLoader.prototype.addLoaderArguements = function (name, value)
{
    // Add the name/value pair to the request data.
    if (this.data.length > 0)
    {
        this.data += "&";
    }
    this.data += window.escape(name) + "=" + window.escape(value);
    this.operation = "?";    
};

//
// Implementation of the XmlLoader.initializeRequest() method.
//
XmlLoader.prototype.setLoaderRequestOptions = function (requestOperation, synchronization)
{
    this.XmlLoaderObj.open(requestOperation, this.url + this.operation + this.data, synchronization);

    this.XmlLoaderObj.setRequestHeader("Content-Type", "text/xml");
};


//
// Implementation of the XmlLoader.submit() method.
//
XmlLoader.prototype.submitLoaderRequest = function (requestOperation, synchronization)
{
    var info = "";
    
    try
    {
        // Set up a synchronous GET request, set the data encoding header and send it.
        if (synchronization) {  // Specify the function that will handle the HTTP response
            this.XmlLoaderObj.onreadystatechange = XmlLoaderHandleResponse;
        }
 
        this.setLoaderRequestOptions(requestOperation, synchronization);
        
        if(!synchronization) { 
            this.XmlLoaderObj.send("");
            // Check the HTTP response status code. If it is not "OK," throw an exception.
            if (this.XmlLoaderObj.status != 200) {
                info = "HTTP request for \"" + this.url + "\" failed with status \"" + this.XmlLoaderObj.status + " " + this.XmlLoaderObj.statusText + "\"";
                
            // Otherwise, return the response data as a text string.
            } else {
                info = this.XmlLoaderObj.responseText;
            }
            
        } else {
            // Send the Add server arguements
            this.XmlLoaderObj.send(this.data);
        }
    }
    catch (e)
    {
        throw "XmlLoader had an error: " + e;
    }
    
    return info;
};

