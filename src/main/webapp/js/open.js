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
		div.style.fontFamily = 'Arial';
		var darkMode = (typeof window.parent.Editor.isDarkMode === 'function' &&
			window.parent.Editor.isDarkMode());

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

		// Function to open server file
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
						window.parent.mxUtils.write(div, window.parent.mxResources.get('noFiles'));
						div.style.color = (darkMode) ? '#cccccc' : '';
						window.parent.mxUtils.br(div);
					}
					else
					{
						// Sorts the array by filename (titles)
						allFiles.sort(function (a, b)
						{
							return a.title.toLowerCase().localeCompare(b.title.toLowerCase());
						});
						
						var table = document.createElement('table');
						table.style.fontSize = '11pt';
						table.style.width = '100%';
						table.style.borderCollapse = 'collapse';
						table.style.tableLayout = 'fixed';
						
						var hrow = document.createElement('tr');
						hrow.style.backgroundColor = (darkMode) ? '#000' : '#D6D6D6';
						hrow.style.color = (darkMode) ? '#cccccc' : '';
						hrow.style.height = '25px';
						hrow.style.textAlign = 'left';
						table.appendChild(hrow);
						
						var hName = document.createElement('th');
						hName.style.width = '40%';
						hName.style.padding = '4px 8px';
						hName.style.overflow = 'hidden';
						hName.style.textOverflow = 'ellipsis';
						window.parent.mxUtils.write(hName, window.parent.mxResources.get('name'));
						hrow.appendChild(hName);
						
						var hModified = document.createElement('th');
						hModified.style.width = '25%';
						hModified.style.padding = '4px 8px';
						window.parent.mxUtils.write(hModified, window.parent.mxResources.get('lastModified'));
						hrow.appendChild(hModified);
						
						var hSize = document.createElement('th');
						hSize.style.width = '15%';
						hSize.style.padding = '4px 8px';
						window.parent.mxUtils.write(hSize, window.parent.mxResources.get('size'));
						hrow.appendChild(hSize);
						
						var hLocation = document.createElement('th');
						hLocation.style.width = '15%';
						hLocation.style.padding = '4px 8px';
						window.parent.mxUtils.write(hLocation, 'Location');
						hrow.appendChild(hLocation);
						
						var hCtrl = document.createElement('th');
						hCtrl.style.width = '5%';
						hCtrl.style.padding = '4px';
						hCtrl.style.textAlign = 'center';
						hrow.appendChild(hCtrl);

						for (var i = 0; i < allFiles.length; i++)
						{
							var fileInfo = allFiles[i];
							
							if (fileInfo.title.length > 0)
							{
								var row = document.createElement('tr');
								row.style.color = (darkMode) ? '#cccccc' : '';
								row.style.height = '28px';
								table.appendChild(row);
								
								if (i & 1 == 1)
								{
									row.style.backgroundColor = (darkMode) ? '#000' : '#E6E6E6';
								}
									
								var nameTd = document.createElement('td');
								nameTd.style.padding = '4px 8px';
								nameTd.style.overflow = 'hidden';
								nameTd.style.textOverflow = 'ellipsis';
								nameTd.style.whiteSpace = 'nowrap';
								nameTd.setAttribute('title', fileInfo.title); // Add tooltip for full filename
								row.appendChild(nameTd);
								var link = document.createElement('a');
								link.style.textDecoration = 'none';
								link.style.color = 'inherit';
								window.parent.mxUtils.write(link, fileInfo.title);
								link.style.cursor = 'pointer';
								nameTd.appendChild(link);
								
								var modifiedTd = document.createElement('td');
								modifiedTd.style.padding = '4px 8px';
								modifiedTd.style.fontSize = '10pt';
								row.appendChild(modifiedTd);
								var str = window.parent.EditorUi.prototype.timeSince(new Date(fileInfo.lastModified));
								
								if (str == null)
								{
									str = window.parent.mxResources.get('lessThanAMinute');
								}
								
								window.parent.mxUtils.write(modifiedTd, window.parent.mxResources.get('timeAgo', [str]));
								
								var sizeTd = document.createElement('td');
								sizeTd.style.padding = '4px 8px';
								sizeTd.style.fontSize = '10pt';
								row.appendChild(sizeTd);
								window.parent.mxUtils.write(sizeTd, window.parent.EditorUi.prototype.formatFileSize(fileInfo.size));
								
								var locationTd = document.createElement('td');
								locationTd.style.padding = '4px 8px';
								locationTd.style.fontSize = '10pt';
								locationTd.style.fontStyle = 'italic';
								locationTd.style.color = fileInfo.isServerFile ? '#0066cc' : '#666666';
								row.appendChild(locationTd);
								window.parent.mxUtils.write(locationTd, fileInfo.isServerFile ? 'Server' : 'Browser');
								
								var ctrlTd = document.createElement('td');
								ctrlTd.style.padding = '4px';
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
														// Use a different URL pattern that includes server file data
														window.parent.geOpenWindow(window.parent.baseUrl + '#Lserver:' + encodeURIComponent(k), function()
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
					closeButton.style.position = 'fixed';
					closeButton.style.bottom = '0px';
					closeButton.style.right = '0px';
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
