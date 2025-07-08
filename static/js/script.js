// static/js/script.js

// Выполняем код только после полной загрузки HTML-структуры
document.addEventListener('DOMContentLoaded', (event) => {

    console.log("DOM fully loaded and parsed"); // Сообщение для отладки

    // --- Логика переключения темы ---
    const themeToggleButton = document.getElementById('theme-toggle-button');
    const body = document.body;

    // Проверяем, существует ли кнопка на странице
    if (themeToggleButton) {
        console.log("Theme toggle button found."); // Отладка

        // Обработчик клика по кнопке
        themeToggleButton.addEventListener('click', () => {
            console.log("Theme toggle button clicked."); // Отладка
            body.classList.toggle('light-mode');
            let currentTheme = body.classList.contains('light-mode') ? 'light' : 'dark';
            console.log(`Theme switched to: ${currentTheme}`);
            try {
                localStorage.setItem('theme', currentTheme);
                console.log(`Theme preference '${currentTheme}' saved to localStorage.`);
            } catch (e) {
                console.error("Failed to save theme preference to localStorage", e);
            }
        });

        // Применение сохраненной темы при загрузке (подстраховка)
        try {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                console.log(`Applying saved theme '${savedTheme}' on DOMContentLoaded.`);
                if (savedTheme === 'light' && !body.classList.contains('light-mode')) {
                    body.classList.add('light-mode');
                } else if (savedTheme === 'dark' && body.classList.contains('light-mode')) {
                    body.classList.remove('light-mode');
                }
            } else {
                 console.log("No theme preference found in localStorage, using default (dark).");
                 if (body.classList.contains('light-mode')) {
                     body.classList.remove('light-mode');
                 }
            }
        } catch (e) {
            console.error("Error applying theme from localStorage on DOMContentLoaded", e);
        }

    } else {
        console.log("Theme toggle button not found on this page.");
    }

    // --- Инициализация intl-tel-input ---
    const phoneInput = document.querySelector("#callback-phone");
    let itiInstance = null; // Переменная для хранения экземпляра библиотеки

    if (phoneInput) {
        console.log("Phone input found, initializing intl-tel-input...");
        try {
            itiInstance = window.intlTelInput(phoneInput, {
                utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.13/js/utils.js",
                initialCountry: "ru",
                preferredCountries: ['ru', 'by', 'kz', 'ua'],
                separateDialCode: true,
                nationalMode: false,
                formatOnDisplay: true,
                hiddenInput: "full_phone"
            });
            console.log("intl-tel-input initialized.");

            phoneInput.addEventListener('keydown', function(event) {
                const key = event.key;
                const isDigit = /^\d$/.test(key);
                const isAllowedControlKey = [
                    'Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab', 'Home', 'End'
                ].includes(key);
                const isModifier = event.ctrlKey || event.metaKey;

                if (!isDigit && !isAllowedControlKey && !isModifier) {
                    event.preventDefault();
                    console.log(`Blocked key: ${key}`);
                }
            });

        } catch (e) {
            console.error("Failed to initialize intl-tel-input:", e);
            if(phoneInput) {
               phoneInput.placeholder = "Ошибка загрузки компонента телефона";
            }
        }
    } else {
        console.log("Phone input #callback-phone not found.");
    }

    // --- Вспомогательные функции для ошибок формы ---
    function setFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        const errorElement = document.getElementById(fieldId + '-error');

        if (!field || !errorElement) {
            console.warn(`Field or error element not found for ID: ${fieldId}`);
            return;
        }

        if (message) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            field.classList.add('is-invalid');
        } else {
            errorElement.textContent = '';
            errorElement.style.display = 'none';
            field.classList.remove('is-invalid');
        }
    }

    function clearAllFormErrors() {
        setFieldError('callback-name', null);
        setFieldError('callback-phone', null);
        setFieldError('callback-lesson-type', null);
        setFieldError('callback-consent', null);
        setFieldError('callback-email', null);
    }


    // --- Логика Модального Окна Обратного Звонка ---
    const callbackForm = document.getElementById('callback-form');
    const successMessage = document.getElementById('callback-success-message');
    const callbackModalEl = document.getElementById('callbackModal');
    const submitButton = callbackForm ? callbackForm.querySelector('button[type="submit"]') : null;

    if (callbackForm && successMessage && callbackModalEl && submitButton) { // phoneInput проверяется выше
        console.log("Callback form elements found for event listener setup.");

        const callbackModal = new bootstrap.Modal(callbackModalEl);

        // Очистка ошибок при вводе/изменении данных в поле
        ['callback-name', 'callback-phone', 'callback-email'].forEach(id => {
            const field = document.getElementById(id);
            if (field) {
                field.addEventListener('input', () => setFieldError(id, null));
            }
        });
        const lessonTypeSelectForClear = document.getElementById('callback-lesson-type');
        if(lessonTypeSelectForClear) {
            lessonTypeSelectForClear.addEventListener('change', () => setFieldError('callback-lesson-type', null));
        }
        const consentCheckboxForClear = document.getElementById('callback-consent');
        if(consentCheckboxForClear) {
            consentCheckboxForClear.addEventListener('change', () => setFieldError('callback-consent', null));
        }

        callbackForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log("Callback form submitted (preventDefault).");

            clearAllFormErrors();

            const nameInput = document.getElementById('callback-name');
            const lessonTypeSelect = document.getElementById('callback-lesson-type');
            const consentCheckbox = document.getElementById('callback-consent');
            const emailInput = document.getElementById('callback-email');
            // phoneInput уже определен глобально для этого блока
            let isValid = true;
            let firstInvalidField = null;

            if (!nameInput.value.trim()) {
                setFieldError('callback-name', 'Пожалуйста, укажите ваше имя.');
                if (!firstInvalidField) firstInvalidField = nameInput;
                isValid = false;
            }

            if (phoneInput) { // Убедимся, что phoneInput существует перед использованием itiInstance
                if (itiInstance) {
                    if (!phoneInput.value.trim()) {
                        setFieldError('callback-phone', 'Пожалуйста, укажите ваш телефон.');
                        if (!firstInvalidField) firstInvalidField = phoneInput;
                        isValid = false;
                    } else if (!itiInstance.isValidNumber()) {
                        setFieldError('callback-phone', 'Пожалуйста, введите корректный номер телефона.');
                        if (!firstInvalidField) firstInvalidField = phoneInput;
                        isValid = false;
                    }
                } else { // Fallback если intl-tel-input не инициализировался, но поле есть
                    if (!phoneInput.value.trim() || phoneInput.value.length < 5) {
                        setFieldError('callback-phone', 'Пожалуйста, укажите ваш телефон.');
                        if (!firstInvalidField) firstInvalidField = phoneInput;
                        isValid = false;
                    }
                }
            } else { // Если самого поля callback-phone нет, это ошибка конфигурации HTML
                 console.error("Phone input field #callback-phone is missing from the form for validation.");
                 // Можно установить isValid = false или обработать иначе
            }

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (emailInput && emailInput.value.trim() && !emailRegex.test(emailInput.value.trim())) {
                setFieldError('callback-email', 'Пожалуйста, введите корректный email адрес.');
                if (!firstInvalidField) firstInvalidField = emailInput;
                isValid = false;
            }

            if (lessonTypeSelect && !lessonTypeSelect.value) {
                setFieldError('callback-lesson-type', 'Пожалуйста, выберите тип занятий.');
                if (!firstInvalidField) firstInvalidField = lessonTypeSelect;
                isValid = false;
            }

            if (consentCheckbox && !consentCheckbox.checked) {
                setFieldError('callback-consent', 'Пожалуйста, дайте согласие на обработку данных.');
                if (!firstInvalidField) firstInvalidField = consentCheckbox;
                isValid = false;
            }

            if (!isValid) {
                if (firstInvalidField) {
                    firstInvalidField.focus();
                }
                return;
            }

            console.log("Form validation passed. Submitting data...");
            submitButton.disabled = true;
            submitButton.textContent = 'Отправка...';

            const formData = new FormData(callbackForm);

            fetch('/submit_callback', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(errData.error || `Ошибка сервера: ${response.status}`);
                    }).catch(() => {
                        throw new Error(`Ошибка сервера: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Server response:', data);
                if (data.success) {
                    showSuccessAndReset();
                } else {
                    alert(`Ошибка: ${data.error || 'Неизвестная ошибка.'}`); // Для серверных ошибок пока alert
                    submitButton.disabled = false;
                    submitButton.textContent = 'Записаться';
                }
            })
            .catch((error) => {
                console.error('Fetch Error:', error);
                alert(`Произошла ошибка при отправке заявки: ${error.message}. Пожалуйста, проверьте соединение или попробуйте позже.`);
                submitButton.disabled = false;
                submitButton.textContent = 'Записаться';
            });
        });

        function showSuccessAndReset() {
             callbackForm.style.display = 'none';
             successMessage.style.display = 'block';
             clearAllFormErrors();

             setTimeout(() => {
                 successMessage.classList.add('visible');
                 console.log("Success message shown.");
             }, 10);

             setTimeout(() => {
                 callbackModal.hide();
                 console.log("Modal hidden after delay.");
                 callbackModalEl.addEventListener('hidden.bs.modal', () => {
                     callbackForm.reset();
                     if (itiInstance && phoneInput) { // Сброс intl-tel-input
                        itiInstance.setCountry("ru");
                     }
                     callbackForm.style.display = 'block';
                     successMessage.style.display = 'none';
                     successMessage.classList.remove('visible');
                     if(submitButton) {
                         submitButton.disabled = false;
                         submitButton.textContent = 'Записаться';
                     }
                     console.log("Form and message reset after modal hidden.");
                 }, { once: true });
             }, 4000);
        }

    } else {
         console.log("One or more callback form elements not found for event listener setup.");
         if (!callbackForm) console.error("Element with ID 'callback-form' not found!");
         if (!successMessage) console.error("Element with ID 'callback-success-message' not found!");
         if (!callbackModalEl) console.error("Element with ID 'callbackModal' not found!");
         // phoneInput проверяется отдельно при инициализации intl-tel-input
         if (!submitButton) console.error("Submit button inside callback form not found!");
    }


    // --- Логика плавной прокрутки к якорям ---
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    if (anchorLinks.length > 0) {
        console.log("Anchor links found for smooth scroll.");
        anchorLinks.forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const hrefAttribute = this.getAttribute('href');
                if (hrefAttribute && hrefAttribute.length > 1 && hrefAttribute !== '#') { // Проверяем, что это не просто '#'
                    try {
                        const targetElement = document.querySelector(hrefAttribute);
                        if (targetElement) {
                            e.preventDefault();
                            console.log(`Scrolling smoothly to ${hrefAttribute}`);
                            targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        } else {
                             console.log(`Target element for ${hrefAttribute} not found.`);
                        }
                    } catch (error) {
                         console.error(`Error finding or scrolling to ${hrefAttribute}:`, error);
                    }
                }
            });
        });
    } else {
         console.log("No anchor links found for smooth scroll.");
    }


    // --- Инициализация AOS (Animate On Scroll) ---
    try {
        if (typeof AOS !== 'undefined') {
            console.log("Initializing AOS library...");
            AOS.init({
                duration: 1000,
                offset: 50,
                once: true,
            });
             console.log("AOS initialized successfully.");
        } else {
            console.log("AOS library not found.");
        }
    } catch (e) {
        console.error("AOS initialization failed", e);
    }


    console.log("Custom scripts execution finished.");

});