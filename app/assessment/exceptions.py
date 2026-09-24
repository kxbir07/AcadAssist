"""Custom domain exceptions for Person 3 Assessment Subsystem."""


class AssessmentError(Exception):
    """Base exception for assessment domain errors."""
    pass


class QuizNotFoundError(AssessmentError):
    """Raised when a requested quiz does not exist."""
    def __init__(self, quiz_id: str):
        super().__init__(f"Quiz with ID '{quiz_id}' was not found.")
        self.quiz_id = quiz_id


class QuizAccessDeniedError(AssessmentError):
    """Raised when a user attempts to access or submit another user's quiz."""
    def __init__(self, quiz_id: str, user_id: str):
        super().__init__(f"User '{user_id}' is not authorized to access quiz '{quiz_id}'.")
        self.quiz_id = quiz_id
        self.user_id = user_id


class QuizAlreadySubmittedError(AssessmentError):
    """Raised when an attempt is submitted for an already evaluated quiz."""
    def __init__(self, quiz_id: str):
        super().__init__(f"Quiz '{quiz_id}' has already been submitted.")
        self.quiz_id = quiz_id


class InvalidQuestionSubmissionError(AssessmentError):
    """Raised when submitted answers contain question IDs not belonging to the quiz."""
    def __init__(self, detail: str):
        super().__init__(detail)


class InsufficientQuestionsError(AssessmentError):
    """Raised when the question pool cannot satisfy unique no-repeat question requirements."""
    def __init__(self, requested: int = 10, available: int = 0, topic: str = "general", message: str = ""):
        super().__init__(
            message or f"Insufficient unique questions available for topic '{topic}'. Requested: {requested}, Available: {available}."
        )
        self.requested = requested
        self.available = available
        self.topic = topic


class InvalidDifficultyError(AssessmentError):
    """Raised when an unrecognized difficulty level is requested."""
    def __init__(self, difficulty: str):
        super().__init__(f"Invalid difficulty '{difficulty}'. Allowed values: easy, medium, hard.")
        self.difficulty = difficulty


class InvalidExamDateError(AssessmentError):
    """Raised when an invalid exam date is provided."""
    def __init__(self, detail: str):
        super().__init__(detail)
