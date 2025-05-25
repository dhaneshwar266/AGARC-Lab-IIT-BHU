// Loading Animation
window.addEventListener('load', () => {
    const loader = document.querySelector('.loading');
    loader.style.opacity = '0';
    setTimeout(() => {
        loader.style.display = 'none';
    }, 500);
});

// Header Scroll Effect
const header = document.querySelector('.header');
window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});

// Smooth Scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Intersection Observer for Animations
const observerOptions = {
    threshold: 0.1
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate');
        }
    });
}, observerOptions);

// Observe all sections
document.querySelectorAll('.section').forEach(section => {
    observer.observe(section);
});

// Gallery Image Modal
const galleryItems = document.querySelectorAll('.gallery-item');
const modal = document.createElement('div');
modal.className = 'modal';
document.body.appendChild(modal);

galleryItems.forEach(item => {
    item.addEventListener('click', () => {
        const img = item.querySelector('img');
        modal.innerHTML = `
            <div class="modal-content">
                <img src="${img.src}" alt="${img.alt}">
                <button class="modal-close">&times;</button>
            </div>
        `;
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    });
});

modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.className === 'modal-close') {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
});

// Form Validation
const contactForm = document.getElementById('contactForm');
if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log("Submitting form..."); // <== DEBUG

        const form = e.target;
        const data = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        const statusDiv = document.getElementById('form-status');

        try {
            submitButton.disabled = true;
            submitButton.textContent = 'Sending...';
            
            const res = await fetch('/contact', { 
                method: 'POST', 
                body: data,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await res.json();
            console.log(result); // <== DEBUG

            if(result.success) {
                statusDiv.innerHTML = '<span style="color:green;">Message sent successfully!</span>';
                statusDiv.style.display = 'block';
                form.reset();
            } else {
                statusDiv.innerHTML = '<span style="color:red;">Failed to send message. Please try again.</span>';
                statusDiv.style.display = 'block';
            }
        } catch (error) {
            console.error("Error submitting form:", error); // <== DEBUG
            statusDiv.innerHTML = '<span style="color:red;">An error occurred. Please try again later.</span>';
            statusDiv.style.display = 'block';
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Send Message';
        }
    });
}

// Remove error class on input
document.querySelectorAll('.form-control').forEach(input => {
    input.addEventListener('input', () => {
        input.classList.remove('error');
    });
});

// Mobile Menu Toggle
const menuToggle = document.querySelector('.menu-toggle');
const navLinks = document.querySelector('.nav-links');
const body = document.body;

if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        navLinks.classList.toggle('active');
        menuToggle.classList.toggle('active');
        body.classList.toggle('menu-open');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (navLinks.classList.contains('active') && 
            !menuToggle.contains(e.target) && 
            !navLinks.contains(e.target)) {
            navLinks.classList.remove('active');
            menuToggle.classList.remove('active');
            body.classList.remove('menu-open');
        }
    });

    // Close menu when clicking on a nav link
    const navItems = navLinks.querySelectorAll('.nav-link');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navLinks.classList.remove('active');
            menuToggle.classList.remove('active');
            body.classList.remove('menu-open');
        });
    });
}

// Parallax Effect
window.addEventListener('scroll', () => {
    const parallaxElements = document.querySelectorAll('.parallax');
    parallaxElements.forEach(element => {
        const speed = element.dataset.speed || 0.5;
        const yPos = -(window.scrollY * speed);
        element.style.transform = `translateY(${yPos}px)`;
    });
});

// Typing Animation
function typeWriter(element, text, speed = 100) {
    let i = 0;
    element.innerHTML = '';
    
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// Initialize typing animation if element exists
const typingElement = document.querySelector('.typing-animation');
if (typingElement) {
    typeWriter(typingElement, typingElement.dataset.text);
}

// Add CSS for new elements
const style = document.createElement('style');
style.textContent = `
    .modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.9);
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }

    .modal-content {
        position: relative;
        max-width: 90%;
        max-height: 90%;
    }

    .modal-content img {
        max-width: 100%;
        max-height: 90vh;
        object-fit: contain;
    }

    .modal-close {
        position: absolute;
        top: -40px;
        right: 0;
        background: none;
        border: none;
        color: white;
        font-size: 30px;
        cursor: pointer;
    }

    .error {
        border-color: red !important;
    }

    .menu-toggle {
        display: none;
        cursor: pointer;
    }

    @media (max-width: 768px) {
        .menu-toggle {
            display: block;
        }

        .nav-links {
            position: fixed;
            top: 70px;
            left: 0;
            width: 100%;
            background: white;
            padding: 20px;
            transform: translateY(-100%);
            transition: transform 0.3s ease;
        }

        .nav-links.active {
            transform: translateY(0);
        }
    }
`;

document.head.appendChild(style); 

document.querySelectorAll('.faq-question').forEach(question => {
    question.addEventListener('click', () => {
        const item = question.parentElement;

        item.classList.toggle('active');
    });
});

document.addEventListener('DOMContentLoaded', function () {
    // Remove the visit counter code since we're using server-side counting now
    // ... rest of your existing code ...
});

// Notice Board and Research Section Animations
// document.addEventListener('DOMContentLoaded', function() {
//     // Clone notice items for smooth infinite scroll
//     const noticeContent = document.querySelector('.notice-board');
//     if (noticeContent) {
//         const notices = noticeContent.innerHTML;
//         noticeContent.innerHTML = `<div class="notice-content">${notices}${notices}</div>`;
//     }
//
//     // Clone research cards for smooth infinite scroll
//     const researchContent = document.querySelector('.research-grid');
//     if (researchContent) {
//         const research = researchContent.innerHTML;
//         researchContent.innerHTML = `<div class="research-content">${research}${research}</div>`;
//     }
// });

// Video Gallery Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Scroll Animation
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    
    function checkScroll() {
        animateElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            
            if (elementTop < windowHeight * 0.8) {
                element.classList.add('visible');
            }
        });
    }
    
    // Initial check
    checkScroll();
    
    // Check on scroll
    window.addEventListener('scroll', checkScroll);
    
    // Video Modal Functionality
    const videoModal = document.querySelector('.video-modal');
    const modalVideo = videoModal.querySelector('video');
    const closeModal = document.querySelector('.close-modal');
    const playButtons = document.querySelectorAll('.play-button');
    
    // Debug log
    console.log('Found play buttons:', playButtons.length);
    
    playButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const videoSrc = this.getAttribute('data-video');
            console.log('Clicked play button for video:', videoSrc);
            
            if (videoSrc) {
                const videoPath = `static/images/${videoSrc}`;
                console.log('Loading video from:', videoPath);
                
                // Set video source
                modalVideo.querySelector('source').src = videoPath;
                modalVideo.load();
                
                // Show modal
                videoModal.style.display = 'flex';
                setTimeout(() => {
                    videoModal.classList.add('active');
                }, 10);
                
                // Play video
                modalVideo.play()
                    .then(() => {
                        console.log('Video started playing successfully');
                    })
                    .catch(error => {
                        console.error('Error playing video:', error);
                        // Show error message to user
                        alert('Error playing video. Please try again.');
                        // Close modal
                        closeVideoModal();
                    });
            } else {
                console.error('No video source specified');
                alert('Video source not found');
            }
        });
    });
    
    function closeVideoModal() {
        videoModal.classList.remove('active');
        setTimeout(() => {
            videoModal.style.display = 'none';
            modalVideo.pause();
            modalVideo.currentTime = 0;
        }, 300);
    }
    
    closeModal.addEventListener('click', closeVideoModal);
    
    // Close modal when clicking outside
    videoModal.addEventListener('click', function(e) {
        if (e.target === videoModal) {
            closeVideoModal();
        }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && videoModal.classList.contains('active')) {
            closeVideoModal();
        }
    });
});

// Video Modal Functions
function openVideo(videoSrc) {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    
    // Set video source
    video.querySelector('source').src = `static/images/${videoSrc}`;
    video.load();
    
    // Show modal
    modal.style.display = 'flex';
    
    // Play video and ensure it loops
    video.loop = true;
    video.play().catch(error => {
        console.error('Error playing video:', error);
        alert('Error playing video. Please try again.');
        closeVideo();
    });
}

function closeVideo() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    
    // Hide modal
    modal.style.display = 'none';
    
    // Reset video
    video.pause();
    video.currentTime = 0;
}

// Initialize thumbnail videos
document.addEventListener('DOMContentLoaded', function() {
    const thumbnailVideos = document.querySelectorAll('.video-thumbnail video');
    thumbnailVideos.forEach(video => {
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.play().catch(error => {
            console.log('Autoplay prevented:', error);
        });
    });
});

// Close modal when clicking outside
document.getElementById('videoModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeVideo();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && document.getElementById('videoModal').style.display === 'flex') {
        closeVideo();
    }
});
