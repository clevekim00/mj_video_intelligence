package com.mj.video.analysis;

import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.MediaType;

import java.net.URI;
import java.util.UUID;
import java.util.Map;

@RestController
@RequestMapping("/api/analyses")
public class AnalysisController {
    private final AnalysisService service;

    public AnalysisController(AnalysisService service) {
        this.service = service;
    }

    @PostMapping
    public ResponseEntity<AnalysisModels.AnalysisJob> create(
            @Valid @RequestBody AnalysisModels.CreateAnalysisRequest request) {
        var job = service.create(request);
        return ResponseEntity.accepted()
                .location(URI.create("/api/analyses/" + job.id()))
                .body(job);
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<AnalysisModels.AnalysisJob> upload(
            @RequestParam String objective,
            @RequestParam MultipartFile file) throws java.io.IOException {
        if (objective == null || objective.isBlank() || file.isEmpty()) {
            throw new IllegalArgumentException("objective and a non-empty video file are required");
        }
        var schema = Map.<String, Object>of(
                "type", "object",
                "required", java.util.List.of("findings"),
                "properties", Map.of("findings", Map.of("type", "array")));
        var request = new AnalysisModels.UploadAnalysisRequest(
                objective,
                schema,
                file.getOriginalFilename() == null ? "uploaded-video" : file.getOriginalFilename(),
                file.getContentType(),
                file.getBytes());
        var job = service.createUpload(request);
        return ResponseEntity.accepted()
                .location(URI.create("/api/analyses/" + job.id()))
                .body(job);
    }

    @GetMapping("/{id}")
    public AnalysisModels.AnalysisJob get(@PathVariable UUID id) {
        return service.get(id);
    }
}
