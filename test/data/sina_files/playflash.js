if(typeof deconcept == "undefined") var deconcept = new Object();
if(typeof deconcept.util == "undefined") deconcept.util = new Object();
if(typeof deconcept.SWFObjectUtil == "undefined") deconcept.SWFObjectUtil = new Object();
deconcept.SWFObject = function(swf, id, w, h, ver, c, quality, xiRedirectUrl, redirectUrl, detectKey) {
	if (!document.getElementById) { return; }
	this.DETECT_KEY = detectKey ? detectKey : 'detectflash';
	this.skipDetect = deconcept.util.getRequestParameter(this.DETECT_KEY);
	this.params = new Object();
	this.variables = new Object();
	this.attributes = new Array();
	if(swf) { this.setAttribute('swf', swf); }
	if(id) { this.setAttribute('id', id); }
	if(w) { this.setAttribute('width', w); }
	if(h) { this.setAttribute('height', h); }
	if(ver) { this.setAttribute('version', new deconcept.PlayerVersion(ver.toString().split("."))); }
	this.installedVer = deconcept.SWFObjectUtil.getPlayerVersion();
	if (!window.opera && document.all && this.installedVer.major > 7) {
		// only add the onunload cleanup if the Flash Player version supports External Interface and we are in IE
		deconcept.SWFObject.doPrepUnload = true;
	}
	if(c) { this.addParam('bgcolor', c); }
	var q = quality ? quality : 'high';
	this.addParam('quality', q);
	this.setAttribute('useExpressInstall', false);
	this.setAttribute('doExpressInstall', false);
	var xir = (xiRedirectUrl) ? xiRedirectUrl : window.location;
	this.setAttribute('xiRedirectUrl', xir);
	this.setAttribute('redirectUrl', '');
	if(redirectUrl) { this.setAttribute('redirectUrl', redirectUrl); }
}
deconcept.SWFObject.prototype = {
	useExpressInstall: function(path) {
		this.xiSWFPath = !path ? "expressinstall.swf" : path;
		this.setAttribute('useExpressInstall', true);
	},
	setAttribute: function(name, value){
		this.attributes[name] = value;
	},
	getAttribute: function(name){
		return this.attributes[name];
	},
	addParam: function(name, value){
		this.params[name] = value;
	},
	getParams: function(){
		return this.params;
	},
	addVariable: function(name, value){
		this.variables[name] = value;
	},
	getVariable: function(name){
		return this.variables[name];
	},
	getVariables: function(){
		return this.variables;
	},
	getVariablePairs: function(){
		var variablePairs = new Array();
		var key;
		var variables = this.getVariables();
		for(key in variables){
			variablePairs[variablePairs.length] = key +"="+ variables[key];
		}
		return variablePairs;
	},
	getSWFHTML: function() {
		var swfNode = "";
		if (navigator.plugins && navigator.mimeTypes && navigator.mimeTypes.length) { // netscape plugin architecture
			if (this.getAttribute("doExpressInstall")) {
				this.addVariable("MMplayerType", "PlugIn");
				this.setAttribute('swf', this.xiSWFPath);
			}
			swfNode = '<embed pluginspage="http://www.macromedia.com/go/getflashplayer" type="application/x-shockwave-flash" src="'+ this.getAttribute('swf') +'" width="'+ this.getAttribute('width') +'" height="'+ this.getAttribute('height') +'" style="'+ this.getAttribute('style') +'"';
			swfNode += ' id="'+ this.getAttribute('id') +'" name="'+ this.getAttribute('id') +'" ';
			var params = this.getParams();
			 for(var key in params){ swfNode += [key] +'="'+ params[key] +'" '; }
			var pairs = this.getVariablePairs().join("&");
			 if (pairs.length > 0){ swfNode += 'flashvars='+ pairs +'&realfull=1&moz=1"'; }
			swfNode += '/>';
		} else { // PC IE
			if (this.getAttribute("doExpressInstall")) {
				this.addVariable("MMplayerType", "ActiveX");
				this.setAttribute('swf', this.xiSWFPath);
			}
			swfNode = '<object id="'+ this.getAttribute('id') +'" classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000" codebase="http://fpdownload.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=9,0,28,0" width="'+ this.getAttribute('width') +'" height="'+ this.getAttribute('height') +'" style="'+ this.getAttribute('style') +'">';
			swfNode += '<param name="movie" value="'+ this.getAttribute('swf') +'" />';
			var params = this.getParams();
			for(var key in params) {
			 swfNode += '<param name="'+ key +'" value="'+ params[key] +'" />';
			}
			var pairs = this.getVariablePairs().join("&");
			if(pairs.length > 0) {swfNode += '<param name="flashvars" value="'+ pairs +'" />';}
			swfNode += "</object>";
		}
		return swfNode;
	},
	write: function(elementId){
		if(this.getAttribute('useExpressInstall')) {
			// check to see if we need to do an express install
			var expressInstallReqVer = new deconcept.PlayerVersion([6,0,65]);
			if (this.installedVer.versionIsValid(expressInstallReqVer) && !this.installedVer.versionIsValid(this.getAttribute('version'))) {
				this.setAttribute('doExpressInstall', true);
				this.addVariable("MMredirectURL", escape(this.getAttribute('xiRedirectUrl')));
				document.title = document.title.slice(0, 47) + " - Flash Player Installation";
				this.addVariable("MMdoctitle", document.title);
			}
		}
		if(this.skipDetect || this.getAttribute('doExpressInstall') || this.installedVer.versionIsValid(this.getAttribute('version'))){
			
		}else{
			if(this.getAttribute('redirectUrl') != "") {
				document.location.replace(this.getAttribute('redirectUrl'));
			}
			
		}
		var n = (typeof elementId == 'string') ? document.getElementById(elementId) : elementId;
		n.innerHTML = this.getSWFHTML();
		return true;
	}
}

/* ---- detection functions ---- */
deconcept.SWFObjectUtil.getPlayerVersion = function(){
	var PlayerVersion = new deconcept.PlayerVersion([0,0,0]);
	if(navigator.plugins && navigator.mimeTypes.length){
		var x = navigator.plugins["Shockwave Flash"];
		if(x && x.description) {
			PlayerVersion = new deconcept.PlayerVersion(x.description.replace(/([a-zA-Z]|\s)+/, "").replace(/(\s+r|\s+b[0-9]+)/, ".").split("."));
		}
	}else if (navigator.userAgent && navigator.userAgent.indexOf("Windows CE") >= 0){ // if Windows CE
		var axo = 1;
		var counter = 3;
		while(axo) {
			try {
				counter++;
				axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash."+ counter);
//				document.write("player v: "+ counter);
				PlayerVersion = new deconcept.PlayerVersion([counter,0,0]);
			} catch (e) {
				axo = null;
			}
		}
	} else { // Win IE (non mobile)
		// do minor version lookup in IE, but avoid fp6 crashing issues
		// see http://blog.deconcept.com/2006/01/11/getvariable-setvariable-crash-internet-explorer-flash-6/
		try{
			var axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.7");
		}catch(e){
			try {
				var axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.6");
				PlayerVersion = new deconcept.PlayerVersion([6,0,21]);
				axo.AllowScriptAccess = "always"; // error if player version < 6.0.47 (thanks to Michael Williams @ Adobe for this code)
			} catch(e) {
				if (PlayerVersion.major == 6) {
					return PlayerVersion;
				}
			}
			try {
				axo = new ActiveXObject("ShockwaveFlash.ShockwaveFlash");
			} catch(e) {}
		}
		if (axo != null) {
			PlayerVersion = new deconcept.PlayerVersion(axo.GetVariable("$version").split(" ")[1].split(","));
		}
	}
	return PlayerVersion;
}
deconcept.PlayerVersion = function(arrVersion){
	this.major = arrVersion[0] != null ? parseInt(arrVersion[0]) : 0;
	this.minor = arrVersion[1] != null ? parseInt(arrVersion[1]) : 0;
	this.rev = arrVersion[2] != null ? parseInt(arrVersion[2]) : 0;
}
deconcept.PlayerVersion.prototype.versionIsValid = function(fv){
	if(this.major < fv.major) return false;
	if(this.major > fv.major) return true;
	if(this.minor < fv.minor) return false;
	if(this.minor > fv.minor) return true;
	if(this.rev < fv.rev) return false;
	return true;
}
/* ---- get value of query string param ---- */
deconcept.util = {
	getRequestParameter: function(param) {
		var q = document.location.search || document.location.hash;
		if (param == null) { return q; }
		if(q) {
			var pairs = q.substring(1).split("&");
			for (var i=0; i < pairs.length; i++) {
				if (pairs[i].substring(0, pairs[i].indexOf("=")) == param) {
					return pairs[i].substring((pairs[i].indexOf("=")+1));
				}
			}
		}
		return "";
	}
}
/* fix for video streaming bug */
deconcept.SWFObjectUtil.cleanupSWFs = function() {
	var objects = document.getElementsByTagName("OBJECT");
	for (var i = objects.length - 1; i >= 0; i--) {
		objects[i].style.display = 'none';
		for (var x in objects[i]) {
			if (typeof objects[i][x] == 'function') {
				objects[i][x] = function(){};
			}
		}
	}
}
// fixes bug in some fp9 versions see http://blog.deconcept.com/2006/07/28/swfobject-143-released/
if (deconcept.SWFObject.doPrepUnload) {
	if (!deconcept.unloadSet) {
		deconcept.SWFObjectUtil.prepUnload = function() {
			__flash_unloadHandler = function(){};
			__flash_savedUnloadHandler = function(){};
			window.attachEvent("onunload", deconcept.SWFObjectUtil.cleanupSWFs);
		}
		window.attachEvent("onbeforeunload", deconcept.SWFObjectUtil.prepUnload);
		deconcept.unloadSet = true;
	}
}
/* add document.getElementById if needed (mobile IE < 5) */
if (!document.getElementById && document.all) { document.getElementById = function(id) { return document.all[id]; }}

/* add some aliases for ease of use/backwards compatibility */
var getQueryParamValue = deconcept.util.getRequestParameter;
var FlashObject = deconcept.SWFObject; // for legacy support
var SWFObject = deconcept.SWFObject;
sinaBokePlayerConfig={
        container:"flash",
        playerWidth:482,
        playerHeight:388,
        pid: 478,
        tid: 2,
        autoLoad: 1,
        autoPlay: 1,
        as: 1,
        tj: 1
};
if(typeof(sinaBokePlayerConfig_o)=='undefined' || sinaBokePlayerConfig_o.length==0 || typeof(sinaBokePlayerConfig_o)=='null'){
    sinaBokePlayerConfig_o=sinaBokePlayerConfig;
}else{
   for(var i in sinaBokePlayerConfig)
   {
       
       if(typeof(sinaBokePlayerConfig_o[i])== 'undefined')
       {
          sinaBokePlayerConfig_o[i] = sinaBokePlayerConfig[i];
       }
   }
}
               
SinaBokePlayer_o = {
	vars_o: sinaBokePlayerConfig_o,
    flashObj: "myMovie",
    $: function(id){
        return document.getElementById(id);
    },
    addVars : function(name, value){
        sinaBokePlayerConfig_o[name] = value;
    },
    showFlashPlayer: function(){
		var userAgent = navigator.userAgent;
		if (userAgent.indexOf("iPad")!=-1 || userAgent.indexOf("iPhone")!=-1){
			this.$(sinaBokePlayerConfig_o.container).innerHTML = "<div style=\"width:" + (this.vars_o.playerWidth-4) + "px;height:" + (this.vars_o.playerHeight-64) + "px;text-align:center;margin:0px auto;padding-top:60px;fong-size:14px;line-height:25px;border:solid 1px #333;\">&#x5947;&#x5999;&#x548C;&#x9769;&#x547D;&#x6027;&#x7684;&#x4F53;&#x9A8C;&#xFF0C;&#x6211;&#x4EEC;&#x79BB;&#x60A8;&#x8D8A;&#x6765;&#x8D8A;&#x8FD1;&#x3002;&#x652F;&#x6301;&#x6280;&#x672F;&#x7814;&#x53D1;&#x4E2D;&#xFF0C;&#x8BF7;&#x7A0D;&#x540E;&#x8BBF;&#x95EE;&#xFF01;<br/>&#x65B0;&#x6D6A;&#x89C6;&#x9891;&#xFF0C;&#x7CBE;&#x5F69;&#x65E0;&#x7586;&#x754C;</div>";
			return;
		}
        var flash = new SWFObject("http://p.you.video.sina.com.cn/swf/BokerPlayerV3_1_1_100401.swf", this.flashObj, this.vars_o.playerWidth, this.vars_o.playerHeight, "9");
        flash.addParam("allowFullScreen", "true");
        flash.addParam("quality", "high");
        flash.addParam("wmode", "transparent");
        flash.addParam("allowScriptAccess", "always");
        for (var key in this.vars_o) {
            flash.addVariable(key, this.vars_o[key]);
        }
        try{
        flash.write(this.$(sinaBokePlayerConfig_o.container));}
        catch(e){alert("errrrrrrrrrrrr:" + e);}         
    },
    setPlayerSize : function(ww, hh){
        this.$(this.flashObj).width = ww;
           this.$(this.flashObj).height = hh;
    }
};

(function(){
    var testSpeed = {
        url: "http://cnt.v.sina.com.cn/quality.php",
        isSentLog: false,
        isHaveLog: false,
        info: "",
        getInfo: function(info, state){
            this.info = info;
            this.isHaveLog = true;
            if (state == "start") {
                this.isSentLog = false;
            }
            if (state == "end") {
                this.send();
                this.isSentLog = true;
            }
        },
        send: function(){
            if (!this.isHaveLog || this.isSentLog) {
                return;
            }
            var endTime = new Date().getTime();
            var img = new Image(1, 1);
            img.src = this.url + "?" + this.info + "&sendTime=" + endTime;
            
            img.onload = function(evt){
                return true;
            };
        }
    };
    
    window["testSpeed_o"] = testSpeed;


    var wasteTraffic = {
        url: "http://cnt.v.sina.com.cn/quality.php?type=langfei",
        info: null,
        getInfo: function(info){
            this.info = info;
        },
        send: function(){
            if (!this.info) {
                return;
            }
            var endTime = new Date().getTime();
            var img = new Image(1, 1);
            img.src = this.url + this.info + "&sendTime=" + endTime;
            img.onload = function(evt){
                return true;
            };
        }
    };
    window["wasteTraffic_o"] = wasteTraffic;

    function unloadEvent(){
        try {
            testSpeed_o.send();
            wasteTraffic_o.send();
        } catch (e) {
            //alert("error:" + e);
        }
        }
        if(window.attachEvent){
        window.attachEvent('onbeforeunload',unloadEvent);
        }else if(window.addEventListener){
        window.addEventListener('beforeunload',unloadEvent,false);
        }else{
                window.onbeforeunload = unloadEvent;
    }
})();