package com.mj.video.analysis;

import org.junit.jupiter.api.Test;
import org.springframework.core.task.SyncTaskExecutor;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AnalysisServiceTest {
    @Test
    void completesAJobWithValidatedPythonResult() {
        var repository = new AnalysisRepository();
        var request = request();
        AnalysisGateway client = ignored -> new AnalysisModels.PythonAnalysisResponse(
                Map.of("restaurants", List.of(Map.of("name", "초당 카페"))), "demo");
        var service = new AnalysisService(repository, client, new SyncTaskExecutor());

        var created = service.create(request);

        assertThat(service.get(created.id()).status()).isEqualTo(AnalysisModels.Status.SUCCEEDED);
        assertThat(service.get(created.id()).mode()).isEqualTo("demo");
    }

    private AnalysisModels.CreateAnalysisRequest request() {
        return new AnalysisModels.CreateAnalysisRequest(
                "맛집 추출",
                Map.of("type", "object"),
                new AnalysisModels.Evidence(
                        "https://example.com/video/1",
                        "강릉 맛집",
                        null,
                        90,
                        List.of(new AnalysisModels.TranscriptSegment(10, 15, "초당 카페")),
                        List.of()));
    }
}
