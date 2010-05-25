
//Sina iAsk Shunqing

//对象引用
function iask_keywords_getElement(id){return document.getElementById(id)};

//发送请求
function iask_keywords_send(mod, value){
	var sender = new Image();
	sender.src = 'http://js.iask.com/' + mod + '?' + value;
	sender.onload = function(){clear(this);};
	sender.onerror = function(){clear(this);};
	sender.onabort = function(){clear(this);};
	function clear(obj){
		obj.onerror = null;
		obj.onload = null;
		obj.onabort = null;
		obj = null;
	}
}

//获取参数
function iask_keywords_getParameter(key){
	var result = null;
	var rs = new RegExp(key + "=([^&]+)","g").exec(self.location.toString());
	if(rs)
		result = rs[1];
	rs = null;
	return result;
}

//设置对象是否显示
function iask_keywords_setDisplay(obj, bool){
	if(bool)
		obj.style.display = '';
	else
		obj.style.display = 'none';
}

//字符长度
function iask_keywords_strLength(str){
	return str.replace(/[^\x00-\xff]/g, "__").length;
}

//初始化
function iask_keywords_ADInit(ADdata){

	var iaskkeyword = iask_keywords_getElement(iask_keywords_lid);

	var show = false;

	if(iaskkeyword && ADdata.length > 0){
		var output = '';

		//根据长度确定显示个数
		var keynum = 0;
		var tmpword = '';
		for(var i = 0; i < ADdata.length; i ++, keynum ++){
			tmpword += ADdata[i].key + '　';
			if(iask_keywords_strLength(tmpword) > iask_keywords_len)
			{
				break;
			}
		}

		//最小长度限制
		show = iask_keywords_strLength(tmpword) > iask_keywords_min;
		if(show){

			for(var i = 0; i < keynum; i ++){
				if(i > 0)
					output += '　';
				//output += '<a href="http://www.google.cn/search?lr=&client=aff-sina&ie=utf8&oe=utf8&hl=zh-CN&channel=contentrelatedsearch&q='
				output += '<a href="http://keyword.sina.com.cn/searchword.php?lr=&c=utf8&client=aff-sina&ie=utf8&oe=utf8&hl=zh-CN&channel=contentrelatedsearch&q='
				output += encodeURIComponent(ADdata[i].key);
				//output += '" target="_blank" onclick=iask_keywords_send("iAskeyword.png","key=' + ADdata[i].key + '&idx=' + i + '")>';
				output += '" target="_blank" onclick=realtimekeywords("'+iask_keywords_url+'","'+ADdata[i].key+'")>';
				output += ADdata[i].key;
				output += '</a>';
			}
			//alert(output);

			iaskkeyword.innerHTML = output;
			iask_keywords_setDisplay(iask_keywords_getElement(iask_keywords_fid), true);

		}

	}

	iask_keywords_send("iAskeyword.png","show=" + show + "&wnum=" + ADdata.length);
}

function realtimekeywords(url,keyword){
	iask_keywords_send("iAskeyword.png","key=" + keyword + "&id=" + i);
	//document.write("<script type=\"javascript/text\" src=\"http://keyword.sina.com.cn/testserver/hotwordtest.php?url="+url+"&keyword="+keyword+"\"></script>");
	var obj = document.createElement('script');
	obj.src = "http://keyword.sina.com.cn/testserver/hotwordtest.php?url="+url+"&keyword="+keyword+"&type=click";
	document.body.appendChild(obj);
	//alert(keyword);
}

function getcook(url){
	var cook = getCookie("SU");
	if(cook == ""){
		//iask_keywords_send("iAskUserLog.png","SU=null&url=" + url);
		//alert("null");
	}
	else{
		iask_keywords_send("iAskUserLog.png","SU=" + cook + "&url=" + url);
		//alert(cook);
	}
}

function sendcook(ids){
	//alert(ids);
	var obj = document.createElement('script');
	obj.type = 'text/javascript';
	obj.src = "http://keywords.sina.com.cn/usertest/iask_gender.php?ids="+ids;
	var loader = document.getElementById(iask_keywords_fid);
	loader.appendChild(obj);
/*	obj[document.all?"onreadystatechange":"onload"] = function(){
		//alert("result send");
		if(getre == 'true'){
			alert(gen+"rate="+rate);
		}
		else{
			alert("no result");
		}
	}
*/
}

function show_gen(){
//function show_gen(getre,gen,rate){
	//alert(re);//getre+gen+rate);
	var expdate = new Date ();
        expdate.setTime(expdate.getTime() + (24 * 3600 * 1000));
	var gen = re['gen'];
	var rate = re['rate'];
	var getre = re['getre'];
	var g = document.cookie.indexOf("SIG=");
	if(getre == 'true'){
		document.cookie = "SIG=" + gen + "; expires=" + expdate.toGMTString() + "; path=/ ; domain=.sina.com.cn";
		//alert("gen="+gen+"  rate="+rate);
	}
	else{
		if(g > 0){
			document.cookie = "SIG=; expires=" + expdate.toGMTString() + "; path=/ ; domain=.sina.com.cn";
		}
		//alert("no result");
	}
}

function precook(ids){
	if(!document.all){
		sendcook(ids);
	}else{
		if (document.readyState=="complete"){
			sendcook(ids);

		} else {
			document.onreadystatechange=function(){
				if(document.readyState=="complete"){
					sendcook(ids);
				}
			}
		}
	}
}

function getKWcook(){
	//alert(urlid);
	//var cook = "";
	var expdate = new Date ();
	expdate.setTime(expdate.getTime() + (3600 * 1000));
	var i = document.cookie.indexOf("SKW=");
	var re = "";
	if(i <= 0){
		return "null";
	}
	else{
		//alert(i);
		var cook = getCookie("SKW");
		re = unescape(cook.substring(cook.indexOf(":")+1,cook.length));
	}
	return re;
}

function setKWcookie(){
	var expdate = new Date ();
	//alert("exe");
        expdate.setTime(expdate.getTime() + (3600 * 1000));
	if(kwstring != "null"){
		//alert(kwstring);
		var string = escape(kwstring);
		document.cookie = "SKW=" + string + "; expires=" + expdate.toGMTString() + "; path=/ ; domain=.sina.com.cn";
	}
}
/*
		if(cook.length > 200){
			if(genb == false){
				var c = cook.substring(cook.indexOf(":")+1,cook.length);
				//alert(cook+"\n"+c);
				re+=c+":"+urlid;
				document.cookie = "SIC=" + c + ":" +urlid + "; expires=" + expdate.toGMTString() + "; path=/ ; domain=.sina.com.cn";
			}
			else{
				re+=cook;
			}
		}else if(cook == ""){
			document.cookie = "SIC=" + urlid + "; expires=" + expdate.toGMTString() + "; path=/ ; domain=.sina.com.cn";
			re+=urlid;
			//setCookie("SIC",urlid);
		}
		else{
			document.cookie = "SIC=" + cook + ":" + urlid + "; expires=" + expdate.toGMTString() + "; path=/ ; domain=.sina.com.cn";
			re+=cook+":"+urlid;
			//setCookie("SIC",cook + urlid);
		}
	}
	//alert(re);
	return re;
	//precook(ids);
}*/
var iask_keywords_url = window.location.href;
var iask_keywords_server = "http://keyword.sina.com.cn/iaskkeywords.php?url=" + iask_keywords_url + "&bid=" + iask_keywords_bid + "&sign=xx&sid=1&dpc=1";

getcook(iask_keywords_url);
//var kwstring=getKWcook();
//alert(kwstring);
//var genstr="http://keyword.sina.com.cn/usertest/adv_test.php?url="+iask_keywords_url+"&kwstring="+kwstring;
//var ADScript = document.createElement('script');
//ADScript.setAttribute("type", "text/javascript");
//ADScript.setAttribute("src", iask_keywords_server);
//document.body.appendChild(ADScript);
document.write("<script type='text/javascript' src='" + iask_keywords_server + "'></script>");
//document.write("<script type='text/javascript' src='" + genstr + "'></script>");

