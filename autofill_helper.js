/**
 * Shubham's JobHunt — Universal ATS 1-Click Form Autofiller
 * 
 * Automatically detects and populates application form fields on:
 * Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Breezy HR, and BambooHR.
 * 
 * Candidate: Shubham Sunil Kadam (ssk080204@gmail.com)
 */
(function() {
  const profile = {
    firstName: "Shubham",
    lastName: "Kadam",
    fullName: "Shubham Sunil Kadam",
    email: "ssk080204@gmail.com",
    phone: "+918169832448",
    location: "Mumbai Metropolitan Region / Remote",
    linkedin: "https://www.linkedin.com/in/shubham-kadam",
    github: "https://github.com/shubhaammm08",
    portfolio: "https://shubhaammm08.github.io/Job-Hunt/",
    summary: "Computer Engineering graduate with hands-on expertise in Python, SQL, Power BI, ETL pipelines, and AI agent automation. Built end-to-end data processing pipelines for Honda motorcycle sales analytics, reducing reporting effort by 80%. Excited to contribute high-impact engineering solutions.",
    noticePeriod: "Immediate / 0-15 days",
    workAuth: "Yes",
    sponsorship: "No",
    gender: "Male"
  };

  function triggerInput(el, val) {
    if (!el || el.disabled || el.readOnly) return;
    el.focus();
    el.value = val;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
  }

  let filledCount = 0;
  const elements = Array.from(document.querySelectorAll('input, textarea, select'));

  elements.forEach(input => {
    if (input.type === 'hidden' || input.type === 'file' || input.type === 'submit') return;

    const name = (input.name || '').toLowerCase();
    const id = (input.id || '').toLowerCase();
    const placeholder = (input.placeholder || '').toLowerCase();
    const aria = (input.getAttribute('aria-label') || '').toLowerCase();
    const autocomplete = (input.autocomplete || '').toLowerCase();
    const label = input.labels && input.labels[0] ? input.labels[0].innerText.toLowerCase() : '';
    const combined = `${name} ${id} ${placeholder} ${aria} ${autocomplete} ${label}`;

    // First Name
    if (combined.includes('first') && (combined.includes('name') || combined.includes('given'))) {
      triggerInput(input, profile.firstName);
      filledCount++;
    }
    // Last Name
    else if (combined.includes('last') && (combined.includes('name') || combined.includes('family') || combined.includes('surname'))) {
      triggerInput(input, profile.lastName);
      filledCount++;
    }
    // Full Name
    else if ((combined.includes('full') && combined.includes('name')) || 
             (combined.includes('name') && !combined.includes('user') && !combined.includes('company') && !combined.includes('file') && !combined.includes('first') && !combined.includes('last'))) {
      triggerInput(input, profile.fullName);
      filledCount++;
    }
    // Email
    else if (combined.includes('email') || input.type === 'email') {
      triggerInput(input, profile.email);
      filledCount++;
    }
    // Phone
    else if (combined.includes('phone') || combined.includes('mobile') || combined.includes('contact') || input.type === 'tel') {
      triggerInput(input, profile.phone);
      filledCount++;
    }
    // LinkedIn
    else if (combined.includes('linkedin')) {
      triggerInput(input, profile.linkedin);
      filledCount++;
    }
    // GitHub
    else if (combined.includes('github') || combined.includes('git')) {
      triggerInput(input, profile.github);
      filledCount++;
    }
    // Portfolio / Website
    else if (combined.includes('portfolio') || combined.includes('website') || combined.includes('blog') || combined.includes('personal site') || (combined.includes('url') && !combined.includes('linkedin') && !combined.includes('github'))) {
      triggerInput(input, profile.portfolio);
      filledCount++;
    }
    // Location / City / Address
    else if (combined.includes('city') || combined.includes('location') || combined.includes('address') || combined.includes('residence')) {
      triggerInput(input, profile.location);
      filledCount++;
    }
    // Notice Period
    else if (combined.includes('notice') || combined.includes('availability') || combined.includes('start date')) {
      triggerInput(input, profile.noticePeriod);
      filledCount++;
    }
    // Cover Letter / Pitch
    else if (input.tagName === 'TEXTAREA' && (combined.includes('cover') || combined.includes('letter') || combined.includes('pitch') || combined.includes('note') || combined.includes('comment') || combined.includes('summary') || combined.includes('additional'))) {
      triggerInput(input, profile.summary);
      filledCount++;
    }
  });

  // Handle Radio Buttons & Checkboxes for Work Authorization
  document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(btn => {
    const parentText = (btn.parentElement ? btn.parentElement.innerText : '').toLowerCase();
    const btnVal = (btn.value || '').toLowerCase();
    if ((parentText.includes('authorized') || parentText.includes('legally') || parentText.includes('eligible')) && (parentText.includes('yes') || btnVal === 'yes' || btnVal === '1')) {
      btn.checked = true;
      btn.dispatchEvent(new Event('change', { bubbles: true }));
      filledCount++;
    }
    if ((parentText.includes('sponsorship') || parentText.includes('visa')) && (parentText.includes('no') || btnVal === 'no' || btnVal === '0')) {
      btn.checked = true;
      btn.dispatchEvent(new Event('change', { bubbles: true }));
      filledCount++;
    }
  });

  // Surface status toast
  const banner = document.createElement('div');
  banner.id = 'jobhunt-autofill-toast';
  banner.innerText = `JobHunt: Auto-filled ${filledCount} fields for Shubham Sunil Kadam!`;
  banner.style.cssText = 'position:fixed;top:20px;right:20px;background:#1f6feb;color:#ffffff;padding:12px 18px;border-radius:8px;font-family:-apple-system,sans-serif;font-size:13px;font-weight:600;z-index:999999;box-shadow:0 8px 24px rgba(0,0,0,0.4);border:1px solid #388bfd;';
  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 4000);
})();
