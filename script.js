import shoeData from './depopdata.json' assert {type: 'json'};

let shoes = [];
let shoeIndex = 1;
let currentShoe;

let spaces = [];
let numGridSpaces = 20;

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

let obsession;
// Function to randomly place images on the webpage
function kickoff() {
    // obsession = document.getElementById("current-obsession");
    addNewShoe();
    setInterval(() => {
        checkOnShoes();
    }, 10000); // 10000
}
let synth;
let started = false;

document.getElementById("intro").addEventListener('click', () => {
    if (Tone && !started) {
        started = true;
        // Create a synth and connect it to the main output (your speakers)
        synth = new Tone.Synth().toDestination();

        // set shoedataindex
        shoeIndex = getRandomNumber(0, shoeData.length);

        kickoff();
        document.getElementById('intro').style.color = 'blue';
        // document.getElementById('intro').style.visibility = 'hidden';
    } else {
        location.reload();
    }
});

document.getElementById("intro").addEventListener('touchstart', () => {
    if (Tone && !started) {
        started = true;
        // Create a synth and connect it to the main output (your speakers)
        synth = new Tone.Synth().toDestination();

        // set shoedataindex
        shoeIndex = getRandomNumber(0, shoeData.length);

        kickoff();
        document.getElementById('intro').style.color = 'blue';
        // document.getElementById('intro').style.visibility = 'hidden';
    } else {
        location.reload();
    }
});

let waitingToAddShoe = false;

function addNewShoe() {
    waitingToAddShoe = false;
    currentShoe = new Shoe(shoeData[shoeIndex]);
    shoes.push(currentShoe);
    shoeIndex = (shoeIndex + 1) % shoeData.length;
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
// window.onload = kickoff;
const AMinorScale = ['A3', 'B3', 'C4', 'D4', 'E4', 'F4', 'G4'];
const CMajorScale = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'];

let scales = [AMinorScale, CMajorScale];

let scale = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'];
scale = AMinorScale;

let typingSpeed = 777;

class Shoe {
    constructor(data) {
        typingSpeed -= 50;
        this.typing = true;
        this.pictureIndex = 0;
        this.pictures = data["pictures"];
        this.numPictures = this.pictures.length;

        this.section = document.createElement("section");
        this.section.draggable = true;
        this.section.classList.add("shoe");

        document.addEventListener("click", () => {
            console.log('hi');
        })

        this.description = data.description;
        this.descriptionIndex = 0;

        this.scale = AMinorScale;

        this.img = new Image();
        this.img.src = data["pictures"][this.pictureIndex][6]['url'];
        this.img.draggable = true;

        // const description = document.createElement('div');
        // description.innerText = data["description"];
        // description.classList.add("shoe-description");

        // Set random size (width and height) for the image
        // this.size = getRandomNumber(11, 500);
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
        // this.size = window.innerWidth * 0.11; // 111 px
        this.img.width = this.size;
        this.section.style.width = this.size + "px";
        this.section.style.height = this.size + "px";
        // this.section.style.visibility = "hidden";
        // img.height = size;

        // Set random position for the image
        this.x = getRandomNumber(0, window.innerWidth - this.size);
        this.y = getRandomNumber(0, window.innerHeight - this.size);
        // this.y = yPos;
        // this.y = 0;
        // this.y = window.innerHeight / 2 - this.size / 2;
        const a = getRandomNumber(0, 360);
        this.section.style.left = `${this.x}px`;
        this.section.style.top = `${this.y}px`;
        // section.style.transform = "rotate(" + a + "deg)";


        // Test to calculate height / width
        // this.fontSize = 24;
        this.maxTextWidth = window.innerWidth * 0.9;

        const testDiv = document.createElement("div");
        testDiv.innerText = this.description;
        testDiv.style.fontSize = this.fontSize + "px";
        // testDiv.style.width = this.maxTextWidth + "px";
        testDiv.style.visibility = "hidden";
        testDiv.classList.add("current-obsession");
        testDiv.id = "test";
        main.appendChild(testDiv);
        const maxHeight = testDiv.clientHeight;
        const maxWidth = testDiv.clientWidth;

        this.descriptionWrapper = document.createElement('div');
        this.descriptionWrapper.classList.add("current-obsession");
        this.descriptionWrapper.style.fontSize = this.fontSize + "px";
        this.descriptionWrapper.style.top = `${getRandomNumber(0, window.innerHeight - maxHeight)}px`;
        // this.descriptionWrapper.style.maxWidth = this.maxTextWidth + "px";
        this.descriptionWrapper.style.left = `${getRandomNumber(0, window.innerWidth - maxWidth)}px`;

        // this.mark = document.createElement("mark");
        // this.descriptionWrapper.appendChild(this.mark);
        // this.descriptionWrapper.style.top = `${this.y}px`;
        this.typeDescription();

        // Append the image to the body
        this.section.appendChild(this.img);
        // this.section.appendChild(this.descriptionWrapper);
        main.appendChild(this.section);
        main.appendChild(this.descriptionWrapper);
        this.pictureTimeout = getRandomNumber(100, 1000);

        const offsetOptions = [-0.05];
        // this.yOffset = getRandomFloat(-0.1, 0.1);
        this.yOffset = getRandomChoice(offsetOptions);
        while (this.yOffset == 0) {
            this.yOffset = getRandomFloat(-0.1, 0.1);
        }

        this.xOffset = getRandomFloat(-1, 1);

        this.sampler = new Tone.Sampler({
            urls: {
                "C4": "C4.mp3",
                "D#4": "Ds4.mp3",
                "F#4": "Fs4.mp3",
                "A4": "A4.mp3",
            },
            release: 1,
            baseUrl: "https://tonejs.github.io/audio/salamander/",
        }).toDestination();

        this.typingSpeedOptions = [33, 88, 111, 222, 555, 888, 1111, 2222]; // 11, 55, 88, 
        this.typingSpeed = getRandomChoice(this.typingSpeedOptions);
        this.maxTypingNum = this.typingSpeed;
        this.pictureTimeout = this.typingSpeed;
    }

    speakDescription() {
        var msg = new SpeechSynthesisUtterance(this.description);
        window.speechSynthesis.speak(msg);
    }

    float() {
        setInterval(() => {
            this.y -= this.yOffset;
            this.section.style.top = `${this.y}px`;
            // this.descriptionWrapper.style.top = `${this.y}px`;
        }, 1);
    }

    toTheEnd() {
        this.descriptionIndex = this.description.length;
        this.descriptionWrapper.innerText = this.description.substring(0, this.descriptionIndex);
        this.typing = false;
    }

    typeDescription() {
        let newTimeout = getRandomNumber(1, this.maxTypingNum);
        let triggerAttackLength = getRandomFloat(0.1, 1);
        setTimeout(() => {
            if (this.descriptionIndex <= this.description.length) {
                const nextChar = this.description[this.descriptionIndex - 1];
                if (nextChar && nextChar != " " && nextChar != '\n') {
                    Tone.loaded().then(() => {
                        let note = getRandomChoice(this.scale);
                        this.sampler.triggerAttackRelease(note, triggerAttackLength);
                    })

                    // DANCING
                    this.pictureIndex = (this.pictureIndex + 1) % this.numPictures;
                    this.img.src = this.pictures[this.pictureIndex][6]['url'];
                }
                this.descriptionWrapper.innerText = this.description.substring(0, this.descriptionIndex);
                this.descriptionIndex++;


                this.typeDescription();

                // if (this.typing) {
                //     this.pictureIndex = (this.pictureIndex + 1) % this.numPictures;
                //     this.img.src = this.pictures[this.pictureIndex][6]['url'];
                //     this.dance(this.pictureTimeout)
                // } else {
                //     this.pictureIndex = 0;
                //     this.img.src = this.pictures[this.pictureIndex][6]['url'];
                // }
            } else {
                this.typing = false;

                // DANCING
                this.pictureIndex = 0;
                this.img.src = this.pictures[this.pictureIndex][6]['url'];
            }
        }, this.maxTypingNum); // 47 used to be new timeout
    }

    dance(currTimeout) {
        // this.size = getRandomNumber(11, 555);
        // this.section.style.maxWidth = this.size + "px";
        // this.pictureTimeout = getRandomNumber(100, 1000);
        // this.pictureTimeout = 111;
        setTimeout(() => {
            if (this.typing) {
                this.pictureIndex = (this.pictureIndex + 1) % this.numPictures;
                this.img.src = this.pictures[this.pictureIndex][6]['url'];
                this.dance(this.pictureTimeout)
            } else {
                this.pictureIndex = 0;
                this.img.src = this.pictures[this.pictureIndex][6]['url'];
            }
        }, this.pictureTimeout);
    }
}


