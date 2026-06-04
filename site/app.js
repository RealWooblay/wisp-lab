// reveal on scroll
const revealEls = document.querySelectorAll('.reveal');
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in');
      revealObserver.unobserve(entry.target);
    }
  });
}, { rootMargin: '0px 0px -10% 0px', threshold: 0.12 });
revealEls.forEach((el) => revealObserver.observe(el));

// waitlist
const signup = document.getElementById('signup');
const success = document.getElementById('signup-success');
if (signup) {
  signup.addEventListener('submit', (event) => {
    event.preventDefault();
    const email = document.getElementById('email');
    if (!email.checkValidity()) { email.reportValidity(); return; }
    signup.hidden = true;
    if (success) success.hidden = false;
  });
}
