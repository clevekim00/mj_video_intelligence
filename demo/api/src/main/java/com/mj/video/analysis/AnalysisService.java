package com.mj.video.analysis;

import org.springframework.core.task.TaskExecutor;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.NoSuchElementException;
import java.util.UUID;

@Service
public class AnalysisService {
    private final AnalysisRepository repository;
    private final AnalysisGateway client;
    private final TaskExecutor taskExecutor;

    public AnalysisService(AnalysisRepository repository, AnalysisGateway client, TaskExecutor taskExecutor) {
        this.repository = repository;
        this.client = client;
        this.taskExecutor = taskExecutor;
    }

    public AnalysisModels.AnalysisJob create(AnalysisModels.CreateAnalysisRequest request) {
        var job = repository.save(AnalysisModels.AnalysisJob.queued(UUID.randomUUID()));
        taskExecutor.execute(() -> execute(job.id(), request));
        return job;
    }

    public AnalysisModels.AnalysisJob createUpload(AnalysisModels.UploadAnalysisRequest request) {
        var job = repository.save(AnalysisModels.AnalysisJob.queued(UUID.randomUUID()));
        taskExecutor.execute(() -> executeUpload(job.id(), request));
        return job;
    }

    public AnalysisModels.AnalysisJob get(UUID id) {
        return repository.find(id).orElseThrow(() -> new NoSuchElementException("analysis not found"));
    }

    void execute(UUID id, AnalysisModels.CreateAnalysisRequest request) {
        var job = get(id);
        repository.save(job.processing());
        try {
            var response = client.analyze(request);
            validate(response);
            repository.save(job.succeeded(response));
        } catch (Exception error) {
            repository.save(job.failed(error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage()));
        }
    }

    void executeUpload(UUID id, AnalysisModels.UploadAnalysisRequest request) {
        var job = get(id);
        repository.save(job.processing());
        try {
            var response = client.analyzeUpload(request);
            validate(response);
            repository.save(job.succeeded(response));
        } catch (Exception error) {
            repository.save(job.failed(error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage()));
        }
    }

    private void validate(AnalysisModels.PythonAnalysisResponse response) {
        if (response == null || response.result() == null) {
            throw new IllegalArgumentException("analysis service returned no result");
        }
        if (response.result().isEmpty()) {
            throw new IllegalArgumentException("analysis service returned an empty result object");
        }
    }
}
