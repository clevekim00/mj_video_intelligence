package com.mj.video.analysis;

import org.springframework.stereotype.Repository;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class AnalysisRepository {
    private final Map<UUID, AnalysisModels.AnalysisJob> jobs = new ConcurrentHashMap<>();

    public AnalysisModels.AnalysisJob save(AnalysisModels.AnalysisJob job) {
        jobs.put(job.id(), job);
        return job;
    }

    public Optional<AnalysisModels.AnalysisJob> find(UUID id) {
        return Optional.ofNullable(jobs.get(id));
    }
}
