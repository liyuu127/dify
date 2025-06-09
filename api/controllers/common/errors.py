from werkzeug.exceptions import HTTPException


class FilenameNotExistsError(HTTPException):
    code = 400
    description = "The specified filename does not exist."


class RemoteFileUploadError(HTTPException):
    code = 400
    description = "Error uploading remote file."


# 参数验证失败
class ParameterValidationError(HTTPException):
    code = 400
    description = "Parameter validation failed."
