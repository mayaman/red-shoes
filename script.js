const ROOT_IMAGE_PATH = './brand_new/';
const response = await fetch(ROOT_IMAGE_PATH + 'products.json');
const fullJSON = await response.json();
const shoeData = fullJSON['products'];
const searchParams = new URLSearchParams(window.location.search);
const STATIC_MODE = searchParams.get('mode') === 'manual';
const HAS_TONE = (typeof Tone !== 'undefined');

console.log("Oh, I used to be disgusted");
console.log("Now I try to be amused");
console.log("But since their wings have got rusted");
console.log("You know the angels wanna wear my red shoes");
console.log("★.｡.:*☆:**:. ⓦ𝕖𝓑s𝕚𝓉𝐄 Ｂʸ 𝓶ⓐ𝐲ᗩ 𝐌𝕒𝓝 .:**:.☆*.:｡.★ ♡ www.mayaontheinter.net ♡ 萬美亞");


let shoes = [];
let shoeIndex = 0;
let currentShoe;
const usedShoeIndices = new Set();
let maxShoesCurrentRun = Math.floor(getRandomNumber(0, shoeData.length/2));
console.log("MAXXXXX SHOES THIS RUN: ", maxShoesCurrentRun);

let main = document.getElementById("main");

// Function to get a random number within a range
function getRandomNumber(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getRandomChoice(array) {
    return array[Math.floor(Math.random() * array.length)];
}

function getRandomFloat(min, max) {
    return Math.random() * (max - min) + min;
}

let colorPalette = getRandomChoice([
    ['white', 'red'],
    ['red', 'black'],
    ['black', 'white']
]);

// Function to randomly place images on the webpage
function kickoff() {
    document.body.style.backgroundColor = colorPalette[0];
    if (!STATIC_MODE) {
        addNewShoe();
        setInterval(() => {
            checkOnShoes();
        }, 10000); // 10000
    }
}

if (!STATIC_MODE) {
    setTimeout(() => {
        // set shoedataindex and kick things off regardless of Tone
        shoeIndex = getRandomNumber(0, shoeData.length - 1);
        kickoff();

        const intro = document.getElementById('intro');
        if (intro) {
            intro.style.visibility = 'hidden';
        }
    }, 2222);
} else {
    shoeIndex = getRandomNumber(0, shoeData.length - 1);
    kickoff();
    const intro = document.getElementById('intro');
    if (intro) {
        intro.style.visibility = 'hidden';
    }
}


let waitingToAddShoe = false;

function addNewShoe(options = {}) {
    const { staticMode = false, force = false } = options;
    if (force || shoes.length < maxShoesCurrentRun) {
        waitingToAddShoe = false;
        console.log("adding shoe at index: ", shoeIndex);
        const selectedIndex = shoeIndex;
        currentShoe = new Shoe(shoeData[selectedIndex], { staticMode, dataIndex: selectedIndex });
        console.log('adding shoe at index: ', shoeIndex)
        shoes.push(currentShoe);
        usedShoeIndices.add(shoeIndex);

        if (usedShoeIndices.size >= shoeData.length) {
            usedShoeIndices.clear();
        }

        let nextIndex = shoeIndex;
        let guard = 0;
        while (usedShoeIndices.has(nextIndex) && guard < 1000) {
            nextIndex = getRandomNumber(0, shoeData.length - 1);
            guard += 1;
        }
        shoeIndex = nextIndex;

    } else {
        let stillDancing = false;
        for (let shoe of shoes) {
            if (shoe.typing) {
                stillDancing = true;
                break;
            }
        }

        if (!stillDancing) {
            maxShoesCurrentRun = Math.floor(getRandomNumber(0, shoeData.length/2));
            colorPalette = getRandomChoice([
                ['white', 'red'],
                ['red', 'black'],
                ['black', 'white']
            ]);
            document.body.style.backgroundColor = colorPalette[0];

            // remove all shoes
            shoes.forEach(shoe => shoe.remove());
            shoes = [];
            usedShoeIndices.clear();
            shoeIndex = getRandomNumber(0, shoeData.length - 1);
            addNewShoe();
        }
    }
}

function checkOnShoes() {
    if (!waitingToAddShoe && currentShoe) {
        // Add new shoe
        waitingToAddShoe = true;
        setTimeout(() => {
            waitingToAddShoe = false;
            addNewShoe();
        }, 22);
    }
}

// Call the function to randomly place images when the page loads
const AMinorScale = ['A3', 'B3', 'C4', 'D4', 'E4', 'F4', 'G4'];

class Shoe {
    constructor(data, options = {}) {
        this.staticMode = Boolean(options.staticMode);
        this.dataIndex = typeof options.dataIndex === 'number' ? options.dataIndex : null;

        this.typing = !this.staticMode;
        this.pictureIndex = 0;
        this.pictures = data["images"];
        this.numPictures = this.pictures.length;

        this.section = document.createElement("section");
        this.section.draggable = true;
        this.section.classList.add("shoe");
        this.timeoutIndex = 0;
        this.timeouts = [];
        this.description = data.description;
        this.descriptionIndex = 0;

        this.scale = AMinorScale;

        this.img = new Image();
        this.img.src = ROOT_IMAGE_PATH + this.pictures[this.pictureIndex].path;
        this.img.draggable = true;

        if (window.innerWidth >= 4000) {
            this.size = 444;
            this.fontSize = 86;
        } else if (window.innerWidth >= 2000) {
            this.size = 222;
            this.fontSize = 48;
        } else if (window.innerWidth >= 1000) {
            this.size = 111;
            this.fontSize = 24;
        } else {
            this.size = 88;
            this.fontSize = 24;
        }
        this.pictureTimeout = getRandomNumber(100, 1000);

        this.img.width = this.size;

        this.section.style.width = this.size + "px";
        this.section.style.height = this.size + "px";

        // Set random position for the image
        this.x = getRandomNumber(0, window.innerWidth - this.size);
        this.y = getRandomNumber(0, window.innerHeight - this.size);
        this.section.style.left = `${this.x}px`;
        this.section.style.top = `${this.y}px`;

        this.maxTextWidth = window.innerWidth * 0.9;

        const testDiv = document.createElement("div");
        testDiv.innerText = this.description;
        testDiv.style.fontSize = this.fontSize + "px";
        testDiv.style.visibility = "hidden";
        testDiv.classList.add("current-obsession");
        main.appendChild(testDiv);
        const maxHeight = testDiv.clientHeight;
        const maxWidth = testDiv.clientWidth;
        main.removeChild(testDiv);


        this.descriptionWrapper = document.createElement('div');
        this.descriptionWrapper.classList.add("current-obsession");
        this.descriptionWrapper.style.color = colorPalette[1];
        this.descriptionWrapper.style.fontSize = this.fontSize + "px";

        let descriptionWrapperTop = getRandomNumber(0, window.innerHeight - maxHeight);
        let descriptionWrapperLeft = getRandomNumber(0, window.innerWidth - maxWidth);
        if (descriptionWrapperTop < 0) {
            descriptionWrapperTop = 0;
        }

        this.descriptionWrapper.style.top = `${descriptionWrapperTop}px`;
        this.descriptionWrapper.style.left = `${descriptionWrapperLeft}px`;


        if (this.staticMode) {
            this.descriptionIndex = this.description.length;
            this.descriptionWrapper.innerText = this.description;
            this.typing = false;
        } else {
            this.typeDescription();
        }

        // Append the image to the body
        this.section.appendChild(this.img);
        main.appendChild(this.section);
        main.appendChild(this.descriptionWrapper);

        if (!this.staticMode) {
            const offsetOptions = [-0.05];
            this.yOffset = getRandomChoice(offsetOptions);
            while (this.yOffset == 0) {
                this.yOffset = getRandomFloat(-0.1, 0.1);
            }

            this.xOffset = getRandomFloat(-1, 1);

            this.sampler = null;
            this.samplerReady = false;

            if (HAS_TONE) {
                try {
                    this.sampler = new Tone.Sampler({
                        urls: {
                            "C4": "C4.mp3",
                            "D#4": "Ds4.mp3",
                            "F#4": "Fs4.mp3",
                            "A4": "A4.mp3",
                        },
                        release: 1,
                        baseUrl: "https://tonejs.github.io/audio/salamander/",
                        onload: () => {
                            // All required buffers are ready
                            this.samplerReady = true;
                        },
                        onerror: (err) => {
                            console.warn('Tone sampler failed to load, continuing silently.', err);
                            this.sampler = null;
                            this.samplerReady = false;
                        }
                    }).toDestination();
                } catch (e) {
                    console.warn('Tone sampler setup error, continuing silently.', e);
                    this.sampler = null;
                    this.samplerReady = false;
                }
            }

            this.typingSpeedOptions = [55, 88, 111, 111, 222, 222, 222, 555];
            this.typingSpeed = getRandomChoice(this.typingSpeedOptions);
            this.maxTypingNum = this.typingSpeed;
            this.pictureTimeout = this.typingSpeed;
        } else {
            this.yOffset = 0;
            this.xOffset = 0;
            this.sampler = null;
            this.samplerReady = false;
            this.typingSpeedOptions = [];
            this.typingSpeed = 0;
            this.maxTypingNum = 0;
            this.pictureTimeout = 0;
        }


    }

    toTheEnd() {
        this.descriptionIndex = this.description.length;
        this.descriptionWrapper.innerText = this.description.substring(0, this.descriptionIndex);
        this.typing = false;
    }

    typeDescription() {
        if (this.staticMode) {
            this.descriptionWrapper.innerText = this.description;
            this.typing = false;
            return;
        }
        let newTimeout = getRandomNumber(1, this.maxTypingNum);
        let triggerAttackLength = getRandomFloat(0.1, 1);
        this.timeouts[this.timeoutIndex] = setTimeout(() => {
            if (this.descriptionIndex <= this.description.length) {
                const nextChar = this.description[this.descriptionIndex - 1];
                if (nextChar && nextChar != " " && nextChar != '\n') {
                    if (this.sampler && this.samplerReady && HAS_TONE) {
                        let note = getRandomChoice(this.scale);
                        try {
                            this.sampler.triggerAttackRelease(note, triggerAttackLength);
                        } catch (e) {
                            console.warn('Sampler play failed, disabling sampler.', e);
                            this.sampler = null;
                            this.samplerReady = false;
                        }
                    }

                    // DANCING
                    this.pictureIndex = (this.pictureIndex + 1) % this.numPictures;
                    this.img.src = ROOT_IMAGE_PATH + this.pictures[this.pictureIndex].path;
                }

                this.descriptionWrapper.innerText = this.description.substring(0, this.descriptionIndex);
                this.descriptionIndex++;


                this.typeDescription();

            } else {
                this.typing = false;

                // DANCING
                this.pictureIndex = 0;
                this.img.src = ROOT_IMAGE_PATH + this.pictures[this.pictureIndex].path;
            }
        }, this.maxTypingNum);
    }

    dance() {
        if (this.staticMode) {
            return;
        }

        setTimeout(() => {
            if (this.typing) {
                this.pictureIndex = (this.pictureIndex + 1) % this.numPictures;
                this.img.src = ROOT_IMAGE_PATH + this.pictures[this.pictureIndex].path;
                this.dance(this.pictureTimeout)
            } else {
                this.pictureIndex = 0;
                this.img.src = ROOT_IMAGE_PATH + this.pictures[this.pictureIndex].path;
            }
        }, this.pictureTimeout);
    }

    remove() {
        this.section.remove();
        this.descriptionWrapper.remove();

        for (let i = 0; i < this.timeouts.length; i++) {
            clearTimeout(this.timeouts[i]);
        }
    }
}

if (STATIC_MODE) {
    document.addEventListener('keydown', (event) => {
        if (event.code === 'Space' || event.code === 'ArrowRight') {
            event.preventDefault();
            addNewShoe({ staticMode: true, force: true });
        } else if (event.code === 'ArrowLeft') {
            event.preventDefault();
            removeLastShoe();
        }
    });
}

function removeLastShoe() {
    if (shoes.length === 0) {
        return;
    }
    const lastShoe = shoes.pop();
    let removedIndex = null;
    if (lastShoe) {
        lastShoe.remove();
        if (typeof lastShoe.dataIndex === 'number') {
            removedIndex = lastShoe.dataIndex;
            usedShoeIndices.delete(lastShoe.dataIndex);
        }
    }
    if (removedIndex !== null) {
        shoeIndex = removedIndex;
        return;
    }
    if (shoes.length === 0) {
        shoeIndex = getRandomNumber(0, shoeData.length - 1);
    } else {
        const previous = shoes[shoes.length - 1];
        const previousId = previous && typeof previous.dataIndex === 'number' ? previous.dataIndex : null;
        if (previousId !== null) {
            shoeIndex = previousId;
        }
    }
}
