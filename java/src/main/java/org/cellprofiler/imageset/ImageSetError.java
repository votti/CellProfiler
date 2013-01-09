/**
 * 
 */
package org.cellprofiler.imageset;

import java.util.List;

/**
 * @author Lee Kamentsky
 *
 * Report an error such as a duplicate or missing image in an image set
 */
public class ImageSetError {
	/**
	 * The key of metadata values that defines the image set,
	 * for instance { "Plate1", "A01" } for metadata keys, "Plate" and "Well"
	 */
	final private List<String> key;
	/**
	 * The name of the channel which has missing or duplicate entries.
	 */
	final private String channelName;
	/**
	 * The error message 
	 */
	final private String message;
	public ImageSetError(String channelName, String message, List<String> key) {
		this.channelName = channelName;
		this.message = message;
		this.key = key;
	}
	public String getChannelName() { return channelName; }
	public String getMessage() { return message; }
	public List<String> getKey() { return key; }
	
	@Override
	public String toString() { return message; }
}