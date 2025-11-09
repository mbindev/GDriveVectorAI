"""
Resource Type Detection Utility
Auto-detect resource types from MIME types.
"""

# MIME type to resource type mapping
MIME_TYPE_MAP = {
    # Images
    'image/jpeg': 'image',
    'image/jpg': 'image',
    'image/png': 'image',
    'image/gif': 'image',
    'image/bmp': 'image',
    'image/svg+xml': 'image',
    'image/webp': 'image',
    'image/tiff': 'image',
    
    # PDFs
    'application/pdf': 'pdf',
    
    # Documents
    'application/vnd.google-apps.document': 'document',
    'application/msword': 'document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
    'application/vnd.oasis.opendocument.text': 'document',
    'text/plain': 'document',
    'text/rtf': 'document',
    'application/rtf': 'document',
    
    # Spreadsheets
    'application/vnd.google-apps.spreadsheet': 'spreadsheet',
    'application/vnd.ms-excel': 'spreadsheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'spreadsheet',
    'application/vnd.oasis.opendocument.spreadsheet': 'spreadsheet',
    'text/csv': 'spreadsheet',
    
    # Presentations
    'application/vnd.google-apps.presentation': 'presentation',
    'application/vnd.ms-powerpoint': 'presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'presentation',
    'application/vnd.oasis.opendocument.presentation': 'presentation',
    
    # Videos
    'video/mp4': 'video',
    'video/mpeg': 'video',
    'video/quicktime': 'video',
    'video/x-msvideo': 'video',
    'video/x-ms-wmv': 'video',
    'video/webm': 'video',
    
    # Audio
    'audio/mpeg': 'audio',
    'audio/mp3': 'audio',
    'audio/wav': 'audio',
    'audio/ogg': 'audio',
    'audio/webm': 'audio',
    
    # Archives
    'application/zip': 'archive',
    'application/x-rar-compressed': 'archive',
    'application/x-tar': 'archive',
    'application/gzip': 'archive',
    'application/x-7z-compressed': 'archive',
    
    # Code files
    'text/html': 'code',
    'text/css': 'code',
    'text/javascript': 'code',
    'application/json': 'code',
    'application/xml': 'code',
    'text/xml': 'code',
    
    # Google Drive specific
    'application/vnd.google-apps.folder': 'folder',
    'application/vnd.google-apps.form': 'form',
    'application/vnd.google-apps.drawing': 'drawing',
}


def detect_resource_type(mime_type: str) -> str:
    """
    Detect resource type from MIME type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        Resource type: image, pdf, document, spreadsheet, presentation, 
        video, audio, archive, code, folder, form, drawing, or other
    """
    if not mime_type:
        return 'unknown'
    
    mime_type = mime_type.lower().strip()
    
    # Direct match
    if mime_type in MIME_TYPE_MAP:
        return MIME_TYPE_MAP[mime_type]
    
    # Partial match for common patterns
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    elif mime_type.startswith('text/'):
        # Text files are usually documents unless specifically code
        if any(code_type in mime_type for code_type in ['html', 'css', 'javascript', 'json', 'xml']):
            return 'code'
        return 'document'
    
    # Default
    return 'other'


def get_resource_icon(resource_type: str) -> str:
    """
    Get icon name for a resource type (for UI).
    
    Returns:
        Material-UI icon name or emoji
    """
    icon_map = {
        'image': 'Image',
        'pdf': 'PictureAsPdf',
        'document': 'Description',
        'spreadsheet': 'TableChart',
        'presentation': 'Slideshow',
        'video': 'VideoLibrary',
        'audio': 'AudioFile',
        'archive': 'Archive',
        'code': 'Code',
        'folder': 'Folder',
        'form': 'Assignment',
        'drawing': 'Brush',
        'other': 'InsertDriveFile',
        'unknown': 'Help'
    }
    return icon_map.get(resource_type, 'InsertDriveFile')


def get_resource_color(resource_type: str) -> str:
    """
    Get color for a resource type (for UI).
    
    Returns:
        Hex color code
    """
    color_map = {
        'image': '#4CAF50',  # Green
        'pdf': '#F44336',    # Red
        'document': '#2196F3', # Blue
        'spreadsheet': '#4CAF50', # Green
        'presentation': '#FF9800', # Orange
        'video': '#9C27B0',  # Purple
        'audio': '#E91E63',  # Pink
        'archive': '#795548', # Brown
        'code': '#607D8B',   # Blue Grey
        'folder': '#FFC107', # Amber
        'form': '#00BCD4',   # Cyan
        'drawing': '#FF5722', # Deep Orange
        'other': '#9E9E9E',  # Grey
        'unknown': '#9E9E9E' # Grey
    }
    return color_map.get(resource_type, '#9E9E9E')
