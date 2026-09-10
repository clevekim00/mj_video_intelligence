package com.mj.video.analysis;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class AnalysisModels {
    private AnalysisModels() {}

    public record TranscriptSegment(
            @PositiveOrZero double startSeconds,
            @Positive double endSeconds,
            @NotBlank String text) {}

    public record FrameCandidate(
            @PositiveOrZero double timestampSeconds,
            @NotBlank String artifactRef,
            String text) {}

    public record Evidence(
            @NotBlank String url,
            @NotBlank String title,
            String description,
            @Positive double durationSeconds,
            List<@Valid TranscriptSegment> transcriptSegments,
            List<@Valid FrameCandidate> frameCandidates) {}

    public record CreateAnalysisRequest(
            @NotBlank String objective,
            Map<String, Object> resultSchema,
            @Valid Evidence evidence) {}

    public record PythonAnalysisResponse(Map<String, Object> result, String mode) {}

    public record UploadAnalysisRequest(
            @NotBlank String objective,
            Map<String, Object> resultSchema,
            @NotBlank String filename,
            String contentType,
            byte[] content) {}

    public enum Status { QUEUED, PROCESSING, SUCCEEDED, FAILED }

    @JsonInclude(JsonInclude.Include.ALWAYS)
    public record AnalysisJob(
            UUID id,
            Status status,
            Map<String, Object> result,
            String mode,
            String error,
            Instant createdAt,
            Instant updatedAt) {

        static AnalysisJob queued(UUID id) {
            var now = Instant.now();
            return new AnalysisJob(id, Status.QUEUED, null, null, null, now, now);
        }

        AnalysisJob processing() {
            return new AnalysisJob(id, Status.PROCESSING, null, null, null, createdAt, Instant.now());
        }

        AnalysisJob succeeded(PythonAnalysisResponse response) {
            return new AnalysisJob(id, Status.SUCCEEDED, response.result(), response.mode(), null, createdAt, Instant.now());
        }

        AnalysisJob failed(String message) {
            return new AnalysisJob(id, Status.FAILED, null, null, message, createdAt, Instant.now());
        }
    }
}
