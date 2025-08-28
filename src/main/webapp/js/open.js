// Handles form-submit by preparing to process response
function handleSubmit()
{
	if (window.parent.openNew && window.parent.baseUrl != null)
	{
		window.parent.openFile.setConsumer(null);
		window.parent.open(window.parent.baseUrl);
	}
	
	// NOTE: File is loaded via JS injection into the iframe, which in turn sets the
	// file contents in the parent window. The new window asks its opener if any file
	// contents are available or waits for the contents to become available.
	return true;
};

// Hides this dialog
function hideWindow(cancel)
{
	if (window.parent.openFile != null)
	{
		window.parent.openFile.cancel(cancel);
	}
};

function fileChanged()
{
	var form = window.openForm || document.getElementById('openForm');
	var openButton = document.getElementById('openButton');
	
	if (form.upfile.value.length > 0)
	{
		openButton.removeAttribute('disabled');
	}
	else
	{
		openButton.setAttribute('disabled', 'disabled');
	}		
};

function main()
{
	if (window.parent != null && window.parent.Editor != null)
	{
		document.body.innerText = '';
		var div = document.createElement('div');
		div.style.fontFamily = 'Arial, sans-serif';
		var darkMode = (typeof window.parent.Editor.isDarkMode === 'function' &&
			window.parent.Editor.isDarkMode());

		// Enhanced dialog container styling
		div.style.padding = '20px';
		div.style.minWidth = '600px';
		div.style.maxWidth = '900px';
		div.style.minHeight = '400px';
		div.style.maxHeight = '80vh';
		div.style.width = 'auto';
		div.style.height = 'auto';
		div.style.margin = '0 auto';
		div.style.backgroundColor = darkMode ? '#2a2a2a' : '#ffffff';
		div.style.border = darkMode ? '1px solid #444' : '1px solid #ccc';
		div.style.borderRadius = '8px';
		div.style.boxShadow = darkMode ? '0 4px 20px rgba(0,0,0,0.5)' : '0 4px 20px rgba(0,0,0,0.15)';
		div.style.overflow = 'auto';
		div.style.position = 'relative';
		
		// Body styling for better centering
		document.body.style.margin = '0';
		document.body.style.padding = '20px';
		document.body.style.backgroundColor = darkMode ? '#1a1a1a' : '#f5f5f5';
		document.body.style.minHeight = '100vh';
		document.body.style.display = 'flex';
		document.body.style.alignItems = 'flex-start';
		document.body.style.justifyContent = 'center';

		// Function to fetch server files
		function fetchServerFiles(callback) {
			try {
				var xhr = new XMLHttpRequest();
				xhr.open('GET', '/list', true);
				xhr.onreadystatechange = function() {
					if (xhr.readyState === 4) {
						if (xhr.status === 200) {
							try {
								var response = JSON.parse(xhr.responseText);
								// Transform server files to match the expected format
								var serverFiles = response.files.map(function(file) {
									return {
										title: file.filename,
										lastModified: new Date(file.modified).getTime(),
										size: file.size,
										isServerFile: true
									};
								});
								callback(serverFiles);
							} catch (e) {
								console.error('Error parsing server files:', e);
								callback([]);
							}
						} else {
							console.error('Error fetching server files:', xhr.status);
							callback([]);
						}
					}
				};
				xhr.send();
			} catch (e) {
				console.error('Error requesting server files:', e);
				callback([]);
			}
		}

                // Server file opening
                function openServerFile(filename, callback) {
                    var xhr = new XMLHttpRequest();
                    xhr.open('GET', '/open/' + encodeURIComponent(filename), true);
                    xhr.onreadystatechange = function() {
                        if (xhr.readyState === 4) {
                            if (xhr.status === 200) {
                                callback(xhr.responseText);
                            } else {
                                console.error('Error opening server file:', xhr.status);
                                callback(null);
                            }
                        }
                    };
                    xhr.send();
                }

		// Fetch both browser and server files
		window.parent.listBrowserFiles(function(browserFiles) {
			fetchServerFiles(function(serverFiles) {
				if (window.parent != null)
				{
					var allFiles = browserFiles.concat(serverFiles);
					
					if (allFiles.length == 0)
					{
						var emptyMsg = document.createElement('div');
						emptyMsg.style.textAlign = 'center';
						emptyMsg.style.padding = '40px 20px';
						emptyMsg.style.fontSize = '14pt';
						emptyMsg.style.color = darkMode ? '#cccccc' : '#666666';
						window.parent.mxUtils.write(emptyMsg, window.parent.mxResources.get('noFiles'));
						div.appendChild(emptyMsg);
					}
					else
					{
						// Sorts the array by filename (titles)
						allFiles.sort(function (a, b)
						{
							return a.title.toLowerCase().localeCompare(b.title.toLowerCase());
						});
						
						var table = document.createElement('table');
						table.style.fontSize = '12pt';
						table.style.width = '100%';
						table.style.borderCollapse = 'collapse';
						table.style.tableLayout = 'fixed';
						table.style.marginBottom = '60px'; // Space for close button
						table.style.border = darkMode ? '1px solid #444' : '1px solid #ddd';
						table.style.borderRadius = '4px';
						table.style.overflow = 'hidden';
						
						var hrow = document.createElement('tr');
						hrow.style.backgroundColor = darkMode ? '#333' : '#f0f0f0';
						hrow.style.color = darkMode ? '#ffffff' : '#333333';
						hrow.style.height = '32px';
						hrow.style.textAlign = 'left';
						hrow.style.fontWeight = 'bold';
						hrow.style.borderBottom = darkMode ? '2px solid #555' : '2px solid #ccc';
						table.appendChild(hrow);
						
						var hName = document.createElement('th');
						hName.style.width = '35%';
						hName.style.padding = '8px 12px';
						hName.style.overflow = 'hidden';
						hName.style.textOverflow = 'ellipsis';
						hName.style.fontSize = '11pt';
						window.parent.mxUtils.write(hName, window.parent.mxResources.get('name'));
						hrow.appendChild(hName);
						
						var hModified = document.createElement('th');
						hModified.style.width = '28%';
						hModified.style.padding = '8px 12px';
						hModified.style.fontSize = '11pt';
						window.parent.mxUtils.write(hModified, window.parent.mxResources.get('lastModified'));
						hrow.appendChild(hModified);
						
						var hSize = document.createElement('th');
						hSize.style.width = '12%';
						hSize.style.padding = '8px 12px';
						hSize.style.fontSize = '11pt';
						window.parent.mxUtils.write(hSize, window.parent.mxResources.get('size'));
						hrow.appendChild(hSize);
						
						var hLocation = document.createElement('th');
						hLocation.style.width = '15%';
						hLocation.style.padding = '8px 12px';
						hLocation.style.fontSize = '11pt';
						window.parent.mxUtils.write(hLocation, 'Location');
						hrow.appendChild(hLocation);
						
						var hCtrl = document.createElement('th');
						hCtrl.style.width = '10%';
						hCtrl.style.padding = '8px 12px';
						hCtrl.style.textAlign = 'center';
						hCtrl.style.fontSize = '11pt';
						window.parent.mxUtils.write(hCtrl, 'Actions');
						hrow.appendChild(hCtrl);

						for (var i = 0; i < allFiles.length; i++)
						{
							var fileInfo = allFiles[i];
							
							if (fileInfo.title.length > 0)
							{
								var row = document.createElement('tr');
								row.style.color = darkMode ? '#e0e0e0' : '#333333';
								row.style.height = '36px';
								row.style.borderBottom = darkMode ? '1px solid #444' : '1px solid #eee';
								row.style.cursor = 'pointer';
								row.style.transition = 'background-color 0.2s ease';
								table.appendChild(row);
								
								// Enhanced hover effects
								row.addEventListener('mouseenter', function() {
									this.style.backgroundColor = darkMode ? '#404040' : '#f8f8f8';
								});
								row.addEventListener('mouseleave', function() {
									this.style.backgroundColor = (i & 1 == 1) ? (darkMode ? '#2d2d2d' : '#f5f5f5') : '';
								});
								
								if (i & 1 == 1)
								{
									row.style.backgroundColor = darkMode ? '#2d2d2d' : '#f5f5f5';
								}
									
								var nameTd = document.createElement('td');
								nameTd.style.padding = '8px 12px';
								nameTd.style.overflow = 'hidden';
								nameTd.style.textOverflow = 'ellipsis';
								nameTd.style.whiteSpace = 'nowrap';
								nameTd.setAttribute('title', fileInfo.title); // Add tooltip for full filename
								row.appendChild(nameTd);
								var link = document.createElement('a');
								link.style.textDecoration = 'none';
								link.style.color = darkMode ? '#66b3ff' : '#0066cc';
								link.style.fontWeight = '500';
								link.style.transition = 'color 0.2s ease';
								window.parent.mxUtils.write(link, fileInfo.title);
								link.style.cursor = 'pointer';
								nameTd.appendChild(link);
								
								// Enhanced link hover effects
								link.addEventListener('mouseenter', function() {
									this.style.color = darkMode ? '#99ccff' : '#004499';
								});
								link.addEventListener('mouseleave', function() {
									this.style.color = darkMode ? '#66b3ff' : '#0066cc';
								});
								
								var modifiedTd = document.createElement('td');
								modifiedTd.style.padding = '8px 12px';
								modifiedTd.style.fontSize = '11pt';
								modifiedTd.style.color = darkMode ? '#cccccc' : '#666666';
								row.appendChild(modifiedTd);
								var str = window.parent.EditorUi.prototype.timeSince(new Date(fileInfo.lastModified));
								
								if (str == null)
								{
									str = window.parent.mxResources.get('lessThanAMinute');
								}
								
								window.parent.mxUtils.write(modifiedTd, window.parent.mxResources.get('timeAgo', [str]));
								
								var sizeTd = document.createElement('td');
								sizeTd.style.padding = '8px 12px';
								sizeTd.style.fontSize = '11pt';
								sizeTd.style.color = darkMode ? '#cccccc' : '#666666';
								row.appendChild(sizeTd);
								window.parent.mxUtils.write(sizeTd, window.parent.EditorUi.prototype.formatFileSize(fileInfo.size));
								
								var locationTd = document.createElement('td');
								locationTd.style.padding = '8px 12px';
								locationTd.style.fontSize = '11pt';
								locationTd.style.fontWeight = '500';
								locationTd.style.color = fileInfo.isServerFile ? (darkMode ? '#66b3ff' : '#0066cc') : (darkMode ? '#999999' : '#666666');
								row.appendChild(locationTd);
								window.parent.mxUtils.write(locationTd, fileInfo.isServerFile ? 'Server' : 'Browser');
								
								var ctrlTd = document.createElement('td');
								ctrlTd.style.padding = '8px 12px';
								ctrlTd.style.textAlign = 'center';
								row.appendChild(ctrlTd);
								var img = document.createElement('img');
								img.src = window.parent.Editor.trashImage;
								img.style.cursor = 'pointer';
								img.style.display = 'inline-block';
								img.style.width = '16px';
								img.style.height = '16px';
								img.setAttribute('title', window.parent.mxResources.get('delete'));
								ctrlTd.appendChild(img);
								
								if (darkMode)
								{
									img.style.filter = 'invert(100%)';
								}

								if (fileInfo.isServerFile) {
									// Server file delete - for now disable delete for server files
									img.style.opacity = '0.3';
									img.style.cursor = 'not-allowed';
									img.setAttribute('title', 'Server files cannot be deleted from this interface');
								} else {
									// Browser file delete
									window.parent.mxEvent.addListener(img, 'click', (function(k)
									{
										return function()
										{
											if (window.parent.mxUtils.confirm(window.parent.mxResources.get('delete') + ' "' + k + '"?'))
											{
												window.parent.deleteBrowserFile(k, function()
												{
													window.location.reload();											
												});
											}
										};
									})(fileInfo.title));
								}
			
								// File opening click handler
								if (fileInfo.isServerFile) {
									// Server file opening
									window.parent.mxEvent.addListener(link, 'click', (function(k)
									{
										return function()
										{
											openServerFile(k, function(data)
											{
												if (data && window.parent != null)
												{
													if (window.parent.openNew && window.parent.baseUrl != null)
													{
														var of = window.parent.openFile;
														// Use relative URL to avoid port mismatch issues with MathJax
														// Parse the current URL to ensure we use the same protocol and host
														var currentUrl = new URL(window.location.href);
														var newUrl = currentUrl.protocol + '//' + currentUrl.host + currentUrl.pathname + '#Lserver:' + encodeURIComponent(k);
														window.parent.geOpenWindow(newUrl, function()
														{
															of.cancel(false);
														}, function()
														{
															of.setData(data, k);
														});
													}
													else
													{
														window.parent.openFile.setData(data, k);
													}
												}
												else
												{
													console.error('Failed to load server file:', k);
												}
											});
										};
									})(fileInfo.title));
								} else {
									// Browser file opening (original logic)
									window.parent.mxEvent.addListener(link, 'click', (function(k)
									{
										return function()
										{
											if (window.parent.openNew && window.parent.baseUrl != null)
											{
												var of = window.parent.openFile;
												window.parent.openBrowserFile(k, function(data)
												{
													if (window.parent != null)
													{
														window.parent.geOpenWindow(window.parent.baseUrl + '#L' + encodeURIComponent(k), function()
														{
															of.cancel(false);
														}, function()
														{
															of.setData(data, k);
														});
													}							
												}, function()
												{
													//TODO add error
												});
											}
											else
											{
												window.parent.openBrowserFile(k, function(data)
												{
													if (window.parent != null)
													{
														window.parent.openFile.setData(data, k);
													}
												}, function()
												{
													//TODO add error
												});
											}
										};
									})(fileInfo.title));
								}
							}
						}
						
						div.appendChild(table);
					}
					
					var closeButton = window.parent.mxUtils.button(window.parent.mxResources.get('close'), function()
					{
						hideWindow(true);
					});
					
					closeButton.className = 'geBtn';
					closeButton.style.position = 'absolute';
					closeButton.style.bottom = '15px';
					closeButton.style.right = '20px';
					closeButton.style.padding = '8px 20px';
					closeButton.style.fontSize = '12pt';
					closeButton.style.fontWeight = '500';
					closeButton.style.border = darkMode ? '1px solid #555' : '1px solid #ccc';
					closeButton.style.borderRadius = '4px';
					closeButton.style.backgroundColor = darkMode ? '#404040' : '#f8f8f8';
					closeButton.style.color = darkMode ? '#ffffff' : '#333333';
					closeButton.style.cursor = 'pointer';
					closeButton.style.transition = 'background-color 0.2s ease, border-color 0.2s ease';
					
					// Enhanced button hover effects
					closeButton.addEventListener('mouseenter', function() {
						this.style.backgroundColor = darkMode ? '#505050' : '#e8e8e8';
						this.style.borderColor = darkMode ? '#666' : '#aaa';
					});
					closeButton.addEventListener('mouseleave', function() {
						this.style.backgroundColor = darkMode ? '#404040' : '#f8f8f8';
						this.style.borderColor = darkMode ? '#555' : '#ccc';
					});
					
					div.appendChild(closeButton);
					
					document.body.appendChild(div);
				}
			});
		});
	}
	else
	{
		document.body.innerHTML = 'Missing parent window';
	}
};

window.addEventListener('load', main);
