package com.mj.video.analysis;

@FunctionalInterface
public interface AnalysisGateway {
    AnalysisModels.PythonAnalysisResponse analyze(AnalysisModels.CreateAnalysisRequest request);

    default AnalysisModels.PythonAnalysisResponse analyzeUpload(AnalysisModels.UploadAnalysisRequest request) {
        throw new UnsupportedOperationException("upload analysis is not configured");
    }
}
