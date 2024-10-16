 
let selectedGenerator = 'flux'; // Default generator

// Function to update selected generator when dropdown item is clicked
document.querySelectorAll('.generator-option').forEach(item => {
    item.addEventListener('click', function (e) {
        e.preventDefault();
        selectedGenerator = this.getAttribute('data-generator');
        document.getElementById('selectedGenerator').innerText = `Selected Generator: ${selectedGenerator.charAt(0).toUpperCase() + selectedGenerator.slice(1)}`;
    });
});

// Function to generate a unique ID for each regenerate button and spinner
function generateUniqueId() {
    return Math.random().toString(36).substring(7);
}

async function submitPrompt() {
    const promptInput = document.getElementById('promptInput');
    const chatBody = document.getElementById('chatBody');
    const spinner = document.getElementById('generateSpinner');
    const generateBtn = document.getElementById('generateBtn');

    // Get the user input
    const prompt = promptInput.value;

    if (!prompt.trim()) {
        return; // Do nothing if the input is empty
    }

    // Append the user message to the chat
    chatBody.innerHTML += `
        <div class="user-message">
            <strong>User:</strong><br>${prompt}
        </div>
    `;

    // Clear the input field
    promptInput.value = '';

    // Replace the "Generate Image" button with the spinner
    generateBtn.style.display = 'none';
    spinner.style.display = 'block';

    try {
        // Send the prompt to the server with the selected generator
        const response = await fetch('/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt, generator: selectedGenerator })
        });

        const data = await response.json();
        const uniqueId = generateUniqueId();  // Generate unique ID for the regenerate button and spinner

        if (response.ok) {
            appendToChat('image', data.image_url, selectedGenerator);
        } else {
            chatBody.innerHTML += `
                <div class="bot-message text-danger">
                    <strong>Error:</strong> ${data.error}
                </div>
            `;
        }

    } catch (error) {
        chatBody.innerHTML += `
            <div class="bot-message text-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    } finally {
        // Replace the spinner with the "Generate Image" button
        generateBtn.style.display = 'block';
        spinner.style.display = 'none';

        // Scroll to the bottom of the chat
        chatBody.scrollTop = chatBody.scrollHeight;
    }
}

function appendToChat(contentType, contentUrl, generator) {
    const chatBody = document.getElementById('chatBody');
    const uniqueId = generateUniqueId();
    const contentHtml = contentType === 'image' ? `
        <div class="bot-image">
            <img src="/static/${contentUrl}" alt="Generated Image" style="max-width: 100%; height: auto; border-radius: 5px;">
        </div>
    ` : `
        <div class="bot-video">
            <video controls style="max-width: 100%; height: auto; border-radius: 5px;">
                <source src="/static/${contentUrl}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
    `;

    const newMessage = document.createElement('div');
    newMessage.className = 'bot-message';
    newMessage.innerHTML = `
        <strong>${generator.charAt(0).toUpperCase() + generator.slice(1)}:</strong><br>
        ${contentHtml}
        <div class="image-actions d-flex justify-content-center">
            <div class="download-icon mx-2">
                <a href="/static/${contentUrl}" download>
                    <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-download" viewBox="0 0 16 16">
                        <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5"/>
                        <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708z"/>
                    </svg>
                </a>
            </div>
            <div class="regenerate-icon mx-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-repeat regenerate-btn" id="regenerateBtn-${uniqueId}" data-prompt="" data-generator="${generator}" viewBox="0 0 16 16">
                    <path d="M11 5.466V4H5a4 4 0 0 0-3.584 5.777.5.5 0 1 1-.896.446A5 5 0 0 1 5 3h6V1.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384l-2.36 1.966a.25.25 0 0 1-.41-.192m3.81.086a.5.5 0 0 1 .67.225A5 5 0 0 1 11 13H5v1.466a.25.25 0 0 1-.41.192l-2.36-1.966a.25.25 0 0 1 0-.384l2.36-1.966a.25.25 0 0 1 .41.192V12h6a4 4 0 0 0 3.585-5.777.5.5 0 0 1 .225-.67Z"/>
                </svg>
                <div class="spinner-border spinner-border-sm text-primary" id="regenerateSpinner-${uniqueId}" role="status" style="display: none;">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
            <div class="camera-icon mx-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-camera-video" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M0 5a2 2 0 0 1 2-2h7.5a2 2 0 0 1 1.983 1.738l3.11-1.382A1 1 0 0 1 16 4.269v7.462a1 1 0 0 1-1.406.913l-3.111-1.382A2 2 0 0 1 9.5 13H2a2 2 0 0 1-2-2V5zm11.5 5.175 3.5 1.556V4.269l-3.5 1.556v4.35zM2 4a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h7.5a1 1 0 0 0 1-1V5a1 1 0 0 0-1-1H2z"/>
                </svg>
            </div>
            <div class="edit-icon mx-2" role="button" tabindex="0">
                <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-pencil-square" viewBox="0 0 16 16">
                    <path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/>
                    <path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"/>
                </svg>
            </div>
        </div>
    `;

    // Prepend the new message to the chat body
    chatBody.prepend(newMessage);
}

// Add event listener for "Regenerate" icon clicks
document.addEventListener('click', function (event) {
    if (event.target.classList.contains('regenerate-btn')) {
        const regenerateBtnId = event.target.id;
        const regenerateSpinnerId = `regenerateSpinner-${regenerateBtnId.split('-')[1]}`;
        const prompt = event.target.getAttribute('data-prompt');
        const generator = event.target.getAttribute('data-generator');
        regenerateImage(prompt, generator, regenerateBtnId, regenerateSpinnerId);
    }

    if (event.target.closest('.camera-icon')) {
        const imgElement = event.target.closest('.bot-image').querySelector('img');
        const imagePath = imgElement.src.split('/').pop(); // Extract the file name from the URL

        // Show the video generation modal
        const videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
        videoModal.show();

        // Make the API call to generate the video
        fetch('/generate-video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_url: imagePath })
        })
        .then(response => response.json())
        .then(data => {
            if (data.video_url) {
                // Append the video to the chat
                appendToChat('video', data.video_url, selectedGenerator);
            } else {
                alert('Error generating video: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while generating the video.');
        })
        .finally(() => {
            // Hide the modal when the process is complete (success or error)
            videoModal.hide();
        });
    }

    if (event.target.closest('.edit-icon')) {
        const imgElement = event.target.closest('.bot-image').querySelector('img');
        const imageUrl = imgElement.src;

        // Set the image URL in all modals
        document.getElementById('upscaleImage').src = imageUrl;
        document.getElementById('removeBackgroundImage').src = imageUrl;
        document.getElementById('imageMixerImage').src = imageUrl;

        // Show the edit toolbar
        const editMessage = document.getElementById('editMessage');
        editMessage.style.display = 'block';
    }
});

document.getElementById('promptForm').addEventListener('submit', function(e) {
    e.preventDefault();
    submitPrompt();
});

// Listen for the Enter key and submit the prompt
document.getElementById('promptInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitPrompt();
    }
});

// Clear history when the "Clear History" button is clicked
document.getElementById('clearHistoryBtn').addEventListener('click', async function() {
    try {
        const response = await fetch('/clear-session', { method: 'POST' });
        if (response.ok) {
            const result = await response.json();
            alert(result.message);

            // Clear the chat history in the frontend
            document.getElementById('chatBody').innerHTML = '';
        } else {
            console.error('Failed to clear session.');
        }
    } catch (error) {
        console.error('Error:', error);
    }
});

// Function to load conversation history
async function loadConversationHistory() {
    const chatBody = document.getElementById('chatBody');
    const response = await fetch('/conversation-history');
    const conversation = await response.json();

    // Prepend each message to ensure newest at the top
    conversation.forEach(({ prompt, generator, image_url, video_url }) => {
        const uniqueId = generateUniqueId();

        if (image_url) {
            const newMessage = document.createElement('div');
            newMessage.className = 'bot-message';
            newMessage.innerHTML = `
                <strong>${generator.charAt(0).toUpperCase() + generator.slice(1)}:</strong><br>
                <div class="bot-image">
                    <img src="/static/${image_url}" alt="Generated Image">
                    <div class="image-actions d-flex justify-content-center">
                        <div class="download-icon mx-2">
                            <a href="/download-image/${image_url.split('/').pop()}" download>
                                <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-download" viewBox="0 0 16 16">
                                    <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5"/>
                                    <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708z"/>
                                </svg>
                            </a>
                        </div>
                        <div class="regenerate-icon mx-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-repeat regenerate-btn" id="regenerateBtn-${uniqueId}" data-prompt="${prompt}" data-generator="${generator}" viewBox="0 0 16 16">
                                <path d="M11 5.466V4H5a4 4 0 0 0-3.584 5.777.5.5 0 1 1-.896.446A5 5 0 0 1 5 3h6V1.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384l-2.36 1.966a.25.25 0 0 1-.41-.192m3.81.086a.5.5 0 0 1 .67.225A5 5 0 0 1 11 13H5v1.466a.25.25 0 0 1-.41.192l-2.36-1.966a.25.25 0 0 1 0-.384l2.36-1.966a.25.25 0 0 1 .41.192V12h6a4 4 0 0 0 3.585-5.777.5.5 0 0 1 .225-.67Z"/>
                            </svg>
                            <div class="spinner-border spinner-border-sm text-primary" id="regenerateSpinner-${uniqueId}" role="status" style="display: none;">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <div class="camera-icon mx-2" role="button" tabindex="0" id="generateVideoBtn">
                            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-camera-reels" viewBox="0 0 16 16">
                                <path d="M6 3a3 3 0 1 1-6 0 3 3 0 0 1 6 0M1 3a2 2 0 1 0 4 0 2 2 0 0 0-4 0"/>
                                <path d="M9 6h.5a2 2 0 0 1 1.983 1.738l3.11-1.382A1 1 0 0 1 16 7.269v7.462a1 1 0 0 1-1.406.913l-3.111-1.382A2 2 0 0 1 9.5 16H2a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2zm6 8.73V7.27l-3.5 1.555v4.35zM1 8v6a1 1 0 0 0 1 1h7.5a1 1 0 0 0 1-1V8a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1"/>
                                <path d="M9 6a3 3 0 1 0 0-6 3 3 0 0 0 0 6M7 3a2 2 0 1 1 4 0 2 2 0 0 1-4 0"/>
                            </svg>
                        </div>
                        <div class="edit-icon mx-2" role="button" tabindex="0">
                            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" fill="currentColor" class="bi bi-pencil-square" viewBox="0 0 16 16">
                                <path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/>
                                <path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"/>
                            </svg>
                        </div>
                    </div>
                </div>
            `;
            chatBody.prepend(newMessage);
        }

        if (video_url) {
            const newMessage = document.createElement('div');
            newMessage.className = 'bot-message';
            newMessage.innerHTML = `
                <strong>${generator.charAt(0).toUpperCase() + generator.slice(1)}:</strong><br>
                <div class="bot-video" align="center">
                    <video controls style="max-width: 100%; height: auto; border-radius: 5px;">
                        <source src="/static/${video_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                </div>
            `;
            chatBody.prepend(newMessage);
        }
    });
}

// Call the function on page load
window.addEventListener('load', loadConversationHistory);

document.addEventListener('DOMContentLoaded', function() {
    // Function to add hover and click events to images
    function addImageEvents(img) {
        img.addEventListener('click', function() {
            window.open(this.src, '_blank');
        });
        img.classList.add('hover-enlarge');
    }

    // Add events to the original image
    const originalImage = document.getElementById('upscaleImage');
    addImageEvents(originalImage);

    // Show the edit toolbar when the edit icon is clicked
    document.addEventListener('click', function(event) {
        if (event.target.closest('.edit-icon')) {
            const imgElement = event.target.closest('.bot-image').querySelector('img');
            const imageUrl = imgElement.src;

            // Set the image URL in all modals
            document.getElementById('upscaleImage').src = imageUrl;
            document.getElementById('removeBackgroundImage').src = imageUrl;
            document.getElementById('imageMixerImage').src = imageUrl;

            // Show the edit toolbar
            const editMessage = document.getElementById('editMessage');
            editMessage.style.display = 'block';
        }
    });

    // Close the edit toolbar
    document.getElementById('closeEditMessage').addEventListener('click', () => {
        document.getElementById('editMessage').style.display = 'none';
    });

    // Generate upscale image
    document.getElementById('generateUpscaleBtn').addEventListener('click', async function() {
        const imagePath = originalImage.src.split('/').pop();
        const response = await fetch('/upscale-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_path: imagePath })
        });

        const data = await response.json();
        if (response.ok) {
            const newImage = document.createElement('img');
            newImage.src = `/static/${data.output_url}`; // Correctly construct the URL
            newImage.alt = "Upscaled Image";
            newImage.style = "max-width: 100%; height: auto; border-radius: 5px;";
            document.getElementById('newImagePlaceholder').innerHTML = '';
            document.getElementById('newImagePlaceholder').appendChild(newImage);

            // Add hover and click events to the new image
            addImageEvents(newImage);

            // Display the upscaled image in the chat area
            const chatBody = document.getElementById('chatBody');
            const chatMessage = document.createElement('div');
            chatMessage.className = 'bot-message';
            chatMessage.innerHTML = `
                <strong>Upscaled Image:</strong><br>
                <div align="center">
                    <img src="/static/${data.output_url}" alt="Upscaled Image" class="center-image" style="max-width: 100%; height: auto; border-radius: 5px;" align="center">
                </div>
            `;
            // Prepend the new message to the chat body
            chatBody.prepend(chatMessage);
            chatBody.scrollTop = chatBody.scrollHeight; // Scroll to the bottom
        } else {
            alert('Error: ' + data.error);
        }
    });

    // Save button functionality
    document.getElementById('saveUpscaleBtn').addEventListener('click', function() {
        const newImage = document.querySelector('#newImagePlaceholder img');
        if (newImage) {
            const link = document.createElement('a');
            link.href = newImage.src;
            link.download = 'upscaled_image.png';
            link.click();
        } else {
            alert('No upscaled image to save.');
        }
    });

    // Add functionality for other buttons
    document.getElementById('button2').addEventListener('click', () => {
        // Add your remove background functionality here
        console.log('Remove Background button clicked');
    });

    document.getElementById('button3').addEventListener('click', () => {
        // Add your image mixer functionality here
        console.log('Image Mixer button clicked');
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const upscaleCard = document.getElementById('upscaleCard');
    const upscaleModal = document.getElementById('upscaleModal');
    const closeUpscaleModal = document.getElementById('closeUpscaleModal');

    // Show the upscale card when the "Upscale" button is clicked
    document.getElementById('button1').addEventListener('click', () => {
        upscaleCard.style.display = 'block';
    });

    // Show the upscale modal when the button in the upscale card is clicked
    document.getElementById('triggerUpscaleModal').addEventListener('click', () => {
        upscaleModal.style.display = 'block';
    });

    // Close the upscale modal
    closeUpscaleModal.addEventListener('click', () => {
        upscaleModal.style.display = 'none';
    });

    // Close the modal when clicking outside of it
    window.addEventListener('click', (event) => {
        if (event.target === upscaleModal) {
            upscaleModal.style.display = 'none';
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Show the upscale popup when the "Upscale" button is clicked
    document.getElementById('button1').addEventListener('click', () => {
        document.getElementById('upscalePopup').style.display = 'block';
    });

    // Show the remove background popup when the "Remove Background" button is clicked
    document.getElementById('button2').addEventListener('click', () => {
        document.getElementById('removeBackgroundPopup').style.display = 'block';
    });

    // Show the image mixer popup when the "Image Mixer" button is clicked
    document.getElementById('button3').addEventListener('click', () => {
        document.getElementById('imageMixerPopup').style.display = 'block';
    });

    // Close the edit toolbar
    document.getElementById('closeEditMessage').addEventListener('click', () => {
        document.getElementById('editMessage').style.display = 'none';
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Show the upscale modal
    document.getElementById('button1').addEventListener('click', () => {
        const upscaleModal = new bootstrap.Modal(document.getElementById('upscaleModal'));
        upscaleModal.show();
    });

    // Show the remove background modal
    document.getElementById('button2').addEventListener('click', () => {
        const removeBackgroundModal = new bootstrap.Modal(document.getElementById('removeBackgroundModal'));
        removeBackgroundModal.show();
    });

    // Show the image mixer modal
    document.getElementById('button3').addEventListener('click', () => {
        const imageMixerModal = new bootstrap.Modal(document.getElementById('imageMixerModal'));
        imageMixerModal.show();
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Event listener for the "Generate" button in the upscale modal
    document.getElementById('generateUpscaleBtn').addEventListener('click', async function() {
        const originalImage = document.getElementById('upscaleImage');
        const imagePath = originalImage.src.split('/').pop(); // Extract the image path
        const spinner = document.getElementById('upscaleSpinner');
        const generateBtn = document.getElementById('generateUpscaleBtn');

        // Show the spinner and hide the button
        spinner.style.display = 'block';
        generateBtn.style.display = 'none';

        try {
            const response = await fetch('/upscale-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_path: imagePath })
            });

            const data = await response.json();
            if (response.ok) {
                // Display the upscaled image in the placeholder
                const newImage = document.createElement('img');
                newImage.src = `/static/${data.output_url}`;
                newImage.alt = "Upscaled Image";
                newImage.style = "max-width: 100%; height: auto; border-radius: 5px;";
                const placeholder = document.getElementById('newImagePlaceholder');
                placeholder.innerHTML = ''; // Clear the placeholder
                placeholder.appendChild(newImage);
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while trying to upscale the image.');
        } finally {
            // Hide the spinner and show the button again
            spinner.style.display = 'none';
            generateBtn.style.display = 'block';
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Event listener for camera icon clicks
    document.addEventListener('click', function(event) {
        if (event.target.closest('.camera-icon')) {
            const imgElement = event.target.closest('.bot-image').querySelector('img');
            const imagePath = imgElement.src.split('/').pop(); // Extract the file name from the URL

            // Show the video generation modal
            const videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
            videoModal.show();

            // Make the API call to generate the video
            fetch('/generate-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_url: imagePath })
            })
            .then(response => response.json())
            .then(data => {
                if (data.video_url) {
                    // Append the video to the chat
                    appendToChat('video', data.video_url, selectedGenerator);
                } else {
                    alert('Error generating video: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while generating the video.');
            })
            .finally(() => {
                // Hide the modal when the process is complete (success or error)
                videoModal.hide();
            });
        }
    });
});

// Define the regenerateImage function
async function regenerateImage(prompt, generator, regenerateBtnId, regenerateSpinnerId) {
    const regenerateSpinner = document.getElementById(regenerateSpinnerId);
    const regenerateBtn = document.getElementById(regenerateBtnId);

    // Show the spinner and hide the button
    regenerateSpinner.style.display = 'block';
    regenerateBtn.style.display = 'none';

    try {
        // Send the prompt to the server with the selected generator
        const response = await fetch('/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt, generator: generator })
        });

        const data = await response.json();

        if (response.ok) {
            appendToChat('image', data.image_url, generator);
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while regenerating the image.');
    } finally {
        // Hide the spinner and show the button again
        regenerateSpinner.style.display = 'none';
        regenerateBtn.style.display = 'block';
    }
}

// Ensure the event listener for regenerate buttons is set up
document.addEventListener('click', function (event) {
    if (event.target.classList.contains('regenerate-btn')) {
        const regenerateBtnId = event.target.id;
        const regenerateSpinnerId = `regenerateSpinner-${regenerateBtnId.split('-')[1]}`;
        const prompt = event.target.getAttribute('data-prompt');
        const generator = event.target.getAttribute('data-generator');
        regenerateImage(prompt, generator, regenerateBtnId, regenerateSpinnerId);
    }
});

var w = window.innerWidth,
    h = window.innerHeight,
    canvas = document.getElementById('test'),
    ctx = canvas.getContext('2d'),
    rate = 60,
    arc = 100,
    time,
    count,
    size = 7,
    speed = 20,
    parts = new Array,
    colors = ['red','#f57900','yellow','#ce5c00','#5c3566'];
var mouse = { x: 0, y: 0 };

canvas.setAttribute('width', w);
canvas.setAttribute('height', h);

function create() {
    time = 0;
    count = 0;

    for (var i = 0; i < arc; i++) {
        parts[i] = {
            x: Math.ceil(Math.random() * w),
            y: Math.ceil(Math.random() * h),
            toX: Math.random() * 5 - 1,
            toY: Math.random() * 2 - 1,
            c: colors[Math.floor(Math.random() * colors.length)],
            size: Math.random() * size
        }
    }
}

function particles() {
    ctx.clearRect(0, 0, w, h);
    canvas.addEventListener('mousemove', MouseMove, false);
    for (var i = 0; i < arc; i++) {
        var li = parts[i];
        var distanceFactor = DistanceBetween(mouse, parts[i]);
        distanceFactor = Math.max(Math.min(15 - (distanceFactor / 10), 10), 1);
        ctx.beginPath();
        ctx.arc(li.x, li.y, li.size * distanceFactor, 0, Math.PI * 2, false);
        ctx.fillStyle = li.c;
        ctx.strokeStyle = li.c;
        if (i % 2 == 0)
            ctx.stroke();
        else
            ctx.fill();

        li.x = li.x + li.toX * (time * 0.05);
        li.y = li.y + li.toY * (time * 0.05);

        if (li.x > w) {
            li.x = 0;
        }
        if (li.y > h) {
            li.y = 0;
        }
        if (li.x < 0) {
            li.x = w;
        }
        if (li.y < 0) {
            li.y = h;
        }
    }
    if (time < speed) {
        time++;
    }
    setTimeout(particles, 1000 / rate);
}

function MouseMove(e) {
    mouse.x = e.layerX;
    mouse.y = e.layerY;
}

function DistanceBetween(p1, p2) {
    var dx = p2.x - p1.x;
    var dy = p2.y - p1.y;
    return Math.sqrt(dx * dx + dy * dy);
}

create();
particles();