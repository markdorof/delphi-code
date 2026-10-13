wexport interface FailureBody {
  error: { code: string; message: string };
  data?: unknown;
}

export class ApiFailure extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly data?: unknown,
  ) {
    super(message);
    this.name = "ApiFailure";
  }

  static fromBody(status: number, body: unknown): ApiFailure {
    if (isFailureBody(body)) {
      return new ApiFailure(body.error.code, body.error.message, status, body.data);
    }
    return new ApiFailure("http_error", `The server answered with HTTP ${status}`, status);
  }

  get needsNewServerToken(): boolean {
    return this.code === "unauthorized";
  }
}

function isFailureBody(body: unknown): body is FailureBody {
  if (typeof body !== "object" || body === null || !("error" in body)) {
    return false;
  }
  const error = (body as { error: unknown }).error;
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}
