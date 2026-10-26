// CHATGPT: normalize visible Latin digits to Persian digits, including dynamically added search results.
(() => {
  const digitMap = { "0":"۰", "1":"۱", "2":"۲", "3":"۳", "4":"۴", "5":"۵", "6":"۶", "7":"۷", "8":"۸", "9":"۹" };
  const convert = (value) => value.replace(/[0-9]/g, (digit) => digitMap[digit]);
  const skip = "script,style,code,pre,kbd,samp,input,textarea,select,svg,math";
  const processNode = (root) => {
    if (root.nodeType === Node.TEXT_NODE) {
      if (root.parentElement && !root.parentElement.closest(skip)) {
        const updated = convert(root.nodeValue);
        if (updated !== root.nodeValue) root.nodeValue = updated;
      }
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
    if (root.nodeType === Node.ELEMENT_NODE && root.matches(skip)) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      if (!node.parentElement?.closest(skip)) {
        const updated = convert(node.nodeValue);
        if (updated !== node.nodeValue) node.nodeValue = updated;
      }
    });
  };
  if (document.body) {
    processNode(document.body);
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        record.addedNodes.forEach(processNode);
        if (record.type === "characterData") processNode(record.target);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }
})();
