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


var hilite_button = "../images/button1d.png";
var default_button = "../images/button1.png";
var newWindow;
var location_ref;
var alt_location_ref  = "#";
var button_time = 400;
var elem;
var main_window;

function setMainWindow(win) {
    main_window = win;
}

function setLocationRef(ref) {
    alt_location_ref = ref;
}

function getLocationRef() {
    return alt_location_ref;
}

function setButtonHiliteTime(time) {
    button_time = time;
}

function setButtonImages(default_image, hilite_image) {
    default_button = default_image;
    hilite_button = hilite_image;
}


function changeRadio(el) {
    el.checked = el.checked ? false : true;
    return true;
};

function getContentText(divText, divID) {
    if(divText.length < 500) {
        document.getElementById(divID).innerHTML = "<a>" + divText + "</a>";
    } else {
        document.getElementById(divID).innerHTML="<div id='notesScrollBox'></table><tr><td align='center' valign='center' bgcolor='#ffffff'><textarea cols='62' rows='12' wrap='on' id='scrollTextArea' onkeyup='sTextArea.innerText=scrollTextArea.innerText'>"+ escape(divText) +"</textarea></td></tr><tr bgcolor'#dddddd'><td align='center' bgcolor='#ffffff'><br/></div>";
    }
};

function getContentLine(len, divText, divID) {
    if(len < 8) {
        document.getElementById(divID).innerHTML = "<a>" + divText + "</a>";
    } else {
        var searchTerm = /<br\/>/g;
        divText = divText.replace(searchTerm, "\n");
        document.getElementById(divID).innerHTML="<div id='notesScrollBox'></table><tr><td align='center' valign='center' bgcolor='#FFFFFF'><textarea cols='62' rows='12' wrap='on' id='scrollTextArea' onkeyup='sTextArea.innerText=scrollTextArea.innerText'>"+ escape(divText) +"</textarea></td></tr><tr bgcolor'#dddddd'><td align='center' bgcolor='#ffffff'><br/></div>";
    }
};

function generateHeader(doc, text1, text2) {
    doc.getElementById("header_box").innerHTML=escape("<div class='header_title_class'><div id='hp_blue_logo'><img src='images/hplogo.png' alt=''/></div><div id='header_title'>" + escape(text1) + "</div><div id='header_title2'>" + escape(text1) + "</div><div id='header_subtitle'>" + escape(text2) + "</div><div id='header_subtitle2'>" + escape(text2) + "</div><div id='tux_logo'><img src='images/tux.png' alt=''/></div></div>");
};


function resetButton(button_name) {
    elem.src = default_button;
    window.location.href = location_ref;
    setLocationRef("#");
}

function hiliteButton(button_name) {
    setTimeout('resetButton();', button_time);
    elem = document.getElementById(button_name).childNodes[1];
    elem.src = hilite_button;
}


function indexClickActions(button_name, default_path) {
    //alert("location_ref - Url Path: " + default_path);
    if(default_path == "????") {
        alert("An unimplement path has occured!");
        location_ref = "test";
    }

    location_ref = default_path;
    if(getLocationRef() != "#") {
        location_ref = getLocationRef();
    }
    //alert("location_ref - Url Path: " + location_ref);
    hiliteButton(button_name);
}

function getStoppedStatus(filename) {
    var localPath = GetLocalDataFile(filename);
    //alert("Get Status - Url Path: " + localPath);
    var http = new XmlLoader(localPath);
    var serverResponse = http.submitLoaderRequest("POST", false);
    statusValue = parseInt(serverResponse);
    return statusValue;
}

function setStoppedStatus(filename) {
    var localPath = GetLocalDataFile(filename);
    //alert("Stop Status - Url Path: " + localPath);
    var http = new XmlLoader(localPath);
    http.submitLoaderRequest("POST", false);
}

function todoOnQuit(path) {
    window.location.href = path;
    window.opener.location.href = path;
    indexClickActions( "quit_button", path);
    window.close();
    fixMainWindow();
    setStoppedStatus("signal_stop");
}


function fixMainWindow() {
    var width = 660;
    var height = 500;
    var x = 0.5 * (window.opener.screen.width - width);
    var y = 0.5 * (window.opener.screen.height - height);
    window.opener.resizeTo(width + 2, height + 100);
    window.opener.moveTo(x,y);
    window.opener.reload(true);
}

function openNewWindow(state) {
    var width = 660;
    var height = 500;
    new_window = null;
    var x = 0.5 * (window.screen.width - width);
    var y = 0.5 * (window.screen.height - height);
    window.toolbar.visible = false;
    window.menubar.visible = false;
    if(state != 0) {
        new_window = window.open("http://localhost:8888/welcome","","dependent=0, resizable=0, status=0, toolbar=0, scrollbars=0" + ',width=' + width + ',height=' + height + ',left=' + x + ', top=' + y);
};

    if(new_window != null) {
        window.resizeTo(width - 100, height - 100);
        window.moveTo(x + 100, y + 100);
    }
    return new_window;
}


function GetLocalDataFile(filename)
{
    var localPath = GetAbsoluteFilePath(filename);
    return localPath;
}


function GetAbsoluteFilePath(filename)
{
    var pgURL = document.URL;
    var n = pgURL.lastIndexOf("\/");
    path = pgURL.substring(n+1);
    var newpath = pgURL.replace(path, "");
    newpath = newpath + filename
    return newpath;
}

function swapDisplay(layer)
{
    if (document.getElementById) {
        document.getElementById(layer).style.display = document.getElementById(layer).style.display? "":"block";
    } else if (document.all) {
        document.all[layer].style.display = document.all[layer].style.display? "":"block";
    } else if (document.layers) {
        document.layers[layer].style.display = document.layers[layer].style.display? "":"block";
    }
};

