#!/usr/bin/php

<?php
// This is my attempt at porting Arc90's Readability to PHP
// Based on readability.js version 0.4
// Original URL: http://lab.arc90.com/experiments/readability/js/readability.js
// Arc90's project URL: http://lab.arc90.com/experiments/readability/
// Author: Keyvan Minoukadeh
// Author URL: http://www.keyvan.net
// License: Apache License, Version 2.0
// Requires: PHP5

// Usage: include readability.php in your script and pass your HTML content to grabArticleHtml() for a string, grabArticle() for a DOMElement object

// Alternative usage (uncomment the lines below)
// Usage: call readability.php in your browser passing it the URL of the page you'd like content from:
// readability.php?url=http://medialens.org/alerts/09/090615_the_guardian_climate.php

// phpinfo();
parse_str($_SERVER['argv'][1], $_GET);

if (!isset($_GET['url']) || $_GET['url'] == '') {
	die('Please pass a URL to the script. E.g. readability.php?url=bla.com/story.html');
}
$url = $_GET['url'];
$html = file_get_contents($url);
echo grabArticleHtml($html);


// returns XHTML
function grabArticleHtml($html, $with_title=true) {
	$contentNode = grabArticle($html, $with_title);
	return $contentNode->ownerDocument->saveXML($contentNode);
	// $xml = $contentNode->ownerDocument->saveXML($contentNode);
	// $dom = new DOMDocument;
	// $dom->loadXML($xml);
	// return replaceTags($dom)->saveHTML();
}

// Converts a DOMNodeList to an Array that can be easily foreached
function dnl2array($domnodelist) {
    $return = array();
    for ($i = 0; $i < $domnodelist->length; ++$i) {
        $return[] = $domnodelist->item($i);
    }
    return $return;
}

// returns DOMElement object
function grabArticle($html, $with_title=true) {
	// Replace all doubled-up <BR> tags with <P> tags, and remove fonts.
	$html = preg_replace('!<br ?/?>[ \r\n\s]*<br ?/?>!', '</p><p>', $html);
	$html = preg_replace('!</?font[^>]*>!', '', $html);
	$document = new DOMDocument();
//	$html = mb_convert_encoding($html, 'UTF-8', 'GB2312');
	$html = mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'); 
	@$document->loadHTML($html);
	$document = clean($document, 'script');
	$allParagraphs = $document->getElementsByTagName('p');
	$topDivCount = 0;
	$topDiv = null;
	$topDivParas;
	
	$articleContent = $document->createElement('html');
	
	if ($with_title) {
		// $articleTitle = $document->createElement('h1');
		// Grab the title from the <title> tag and inject it as the title.
		//var_dump($document->getElementsByTagName('title')->item(0)->nodeValue);exit;
		// $articleTitle->appendChild($document->createTextNode($document->getElementsByTagName('title')->item(0)->nodeValue));
		// $articleContent->appendChild($articleTitle);
	  $articleHead = $document->createElement('head');
	  $title = $document->getElementsByTagName('title')->item(0);
	  if ($title != NULL) {
	    $articleHead->appendChild($title);
	  }
	  $metahttp = $document->createElement('meta');
	  $metahttp->setAttribute('http-equiv', 'Content-Type');
	  $metahttp->setAttribute('content', 'text/html; charset=utf-8');
	  $articleHead->appendChild($metahttp);

	  $articleContent->appendChild($articleHead);
	}
	
	// Study all the paragraphs and find the chunk that has the best score.
	// A score is determined by things like: Number of <p>'s, commas, special classes, etc.
	// echo $allParagraphs->length."\n";

	for ($j=0; $j < $allParagraphs->length; $j++) {
		$parentNode = $allParagraphs->item($j)->parentNode;

		// if($parentNode->hasAttribute('class')){
		//   echo "Class: ".$parentNode->getAttributeNode('class')->value."\n";
		// }
		// if($parentNode->hasAttribute('id')){
		//   echo "ID: ".$parentNode->getAttributeNode('id')->value."\n";
		// }

		// Initialize readability data
		if (!$parentNode->hasAttribute('readability'))
		{
			$readability = $document->createAttribute('readability');
			$readability->value = 0;
			$parentNode->appendChild($readability);		

			// Look for a special classname
			if (classNameMatch($parentNode, '/(comment|meta|footer|footnote|articleReview|sideBars)/')) {
				$readability->value -= 50;
			} else if(classNameMatch($parentNode, '/((^|\s)(post|hentry|entry[-]?(content|text|body)?|blkContainerSblkCon|blkContainerPblk|article[-]?(content|text|body)?)(\s|$))/')) {
				$readability->value += 25;
			}

			// Look for a special ID
			if (preg_match('/(comment|meta|footer|footnote)/', $parentNode->getAttribute('id'))) {
				$readability->value -= 50;
			} else if (preg_match('/^(C-Main-Article-QQ|main|content|post|hentry|entry[-]?(content|text|body)?|artibody|article[-]?(content|text|body)?)$/', $parentNode->getAttribute('id'))) {
				$readability->value += 25;
			}
		} else {
			$readability = $parentNode->getAttributeNode('readability');
		}

		// Add a point for the paragraph found
		if(strlen($allParagraphs->item($j)->textContent) > 10) {
			$readability->value++;
		}

		// Add points for any commas within this paragraph
		$readability->value += substr_count($allParagraphs->item($j)->textContent, ',');
		$readability->value += substr_count($allParagraphs->item($j)->textContent, '，');
		$readability->value += substr_count($allParagraphs->item($j)->textContent, '。');

		// echo "Readability: ".$readability->value."\n";

	}

	// Assignment from index for performance. See http://www.peachpit.com/articles/article.aspx?p=31567&seqNum=5 
	$allElements = $document->getElementsByTagName('*');
	$topDiv = null;
	foreach ($allElements as $node) {
		if($node->hasAttribute('readability') && ($topDiv == null || (int)$node->getAttribute('readability') > (int)$topDiv->getAttribute('readability'))) {
			$topDiv = $node;
		}
	}

	if($topDiv == null) {
		// $topDiv = $document->createElement('div', 'Sorry, readability was unable to parse this page for content.');
	} else {
	  // $topDiv = replaceTags($topDiv);
		cleanStyles($topDiv);					// Removes all style attributes
		$topDiv = killDivs($topDiv);				// Goes in and removes DIV's that have more non <p> stuff than <p> stuff
		$topDiv = killBreaks($topDiv);            // Removes any consecutive <br />'s into just one <br /> 

		// Cleans out junk from the topDiv just in case:
		$topDiv = clean($topDiv, 'form');
		$topDiv = clean($topDiv, 'object');
		$topDiv = clean($topDiv, 'table', 250);
		$topDiv = clean($topDiv, 'h1');
		//$topDiv = clean($topDiv, 'h2');
		$topDiv = clean($topDiv, 'iframe');
		$topDiv = clean($topDiv, 'script');
	}
	
	$articleBody = $document->createElement('body');
	if($topDiv != null){
	  // $d = replaceTags($topDiv);
	  // echo $d->saveHTML();
	  $articleBody->appendChild($topDiv);
	}
	$articleContent->appendChild($articleBody);
	  
	// $articleContent->appendChild($topDiv);
	
	return $articleContent;
}

function classNameMatch($node, $pattern) {
	if (!$node->hasAttribute('class')) return false;
	$class = $node->attributes->getNamedItem('class')->nodeValue;
	return preg_match($pattern, $class);
}

function classNameHas($node, $classNames) {
	if (!$node->hasAttribute('class')) return false;
	$class = $node->attributes->getNamedItem('class')->nodeValue;
	$class = explode(' ', $class);
	foreach ($class as $classValue) {
		if (in_array(trim($classValue), $classNames)) return true;
	}
	return false;
}

function cleanStyles($node) {
	$elems = $node->getElementsByTagName('*');
	foreach ($elems as $elem) {
		$elem->removeAttribute('style');
	}
}

function killDivs ($node) {
	$divsList = $node->getElementsByTagName('div');
	$curDivLength = $divsList->length;
	
	// Gather counts for other typical elements embedded within.
	// Traverse backwards so we can remove nodes at the same time without effecting the traversal.
	for ($i=$curDivLength-1; $i >= 0; $i--) {
		$p = $divsList->item($i)->getElementsByTagName('p')->length;
		$img = $divsList->item($i)->getElementsByTagName('img')->length;
		$li = $divsList->item($i)->getElementsByTagName('li')->length;
		$a = $divsList->item($i)->getElementsByTagName('a')->length;
		$embed = $divsList->item($i)->getElementsByTagName('embed')->length;

		// If the number of commas is less than 10 (bad sign) ...
		if (substr_count($divsList->item($i)->textContent, ',') < 10) {
			// And the number of non-paragraph elements is more than paragraphs 
			// or other ominous signs :
			if ( $img > $p || $li > $p || $a > $p || $p == 0 || $embed > 0) {
				$divsList->item($i)->parentNode->removeChild($divsList->item($i));
			}
		}
	}
	return $node;
}

function killBreaks ($node) {
	$pattern = '!(<br\s*/?>(\s|&nbsp;)*){1,}!';
	$xml = $node->ownerDocument->saveXML($node);
	$xml = preg_replace($pattern, '<br />', $xml);
	$f = $node->ownerDocument->createDocumentFragment();
	@$f->appendXML($xml); // @ to prevent PHP warnings
	$node->parentNode->replaceChild($f,$node); 
	return $node;
}

function clean($node, $tag, $minWords=1000000) {
	$targetList = $node->getElementsByTagName($tag);
	$_len = $targetList->length;

	for ($y=$_len-1; $y >=0; $y--) {
		// If the text content isn't laden with words, remove the child:
		if (substr_count($targetList->item($y)->textContent, ' ') < $minWords) {
			$targetList->item($y)->parentNode->removeChild($targetList->item($y));
		}
	}
	return $node;
}

function replaceTags($node) {
  $stylesheet = '<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
<xsl:output method="xml" indent="yes"/>
<!-- the identity template -->

<xsl:template match="@*|node()">
<xsl:copy>
<xsl:apply-templates select="@*|node()"/>
</xsl:copy>
</xsl:template>
 
<xsl:template match="//span">
<xsl:apply-templates/>
</xsl:template>
 
</xsl:stylesheet>
';

  $xsl = new DOMDocument;
  $xsl->loadXML($stylesheet);
  $xp = new XSLTProcessor;
  $xp->importStylesheet($xsl);

  return $xp->transformToDoc($node);
  // return $node;

  // return $xsl;
}

?>
