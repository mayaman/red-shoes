// import puppeteer from 'puppeteer';
// import { puppeteer } from 'puppeteer';
const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    await page.setUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
    await page.goto('https://www.depop.com/search/?q=ballet+flats&categories=14&colours=red&sort=relevance');

    const acceptButton = await page.waitForSelector(".fFJfAu");
    //   await page.focus(acceptButton);

    console.log(acceptButton);
    await acceptButton.click();

    await autoScroll(page);

    const urls = await page.evaluate(() => Array.from(
        document.querySelectorAll('a'), (link) => {

            const newLink = link.href;

            if (newLink.indexOf('products') > 0) {
                return newLink;
            }
        }
    ));

    // console.log(urls, { 'maxArrayLength': null });

    urls.forEach((url) => {

        if (url) {
            console.log(JSON.stringify(url) + ',');
        }
    });


    // Dispose of handle
    await acceptButton.dispose();

    await page.screenshot({ path: 'redflats.png' });



    await browser.close();
})();

async function autoScroll(page) {
    await page.evaluate(async () => {
        await new Promise((resolve) => {
            var totalHeight = 0;
            var distance = 100;
            var timer = setInterval(() => {
                var scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeight - window.innerHeight) {
                    clearInterval(timer);
                    resolve();
                }
            }, 100);
        });
    });
}