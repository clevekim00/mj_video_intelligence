package com.mj.video.analysis;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.http.client.SimpleClientHttpRequestFactory;

@Component
public class AnalysisClient implements AnalysisGateway {
    private final RestClient client;
    private final ObjectMapper objectMapper;

    public AnalysisClient(
            RestClient.Builder builder,
            ObjectMapper objectMapper,
            @Value("${analysis-service.base-url}") String baseUrl) {
        this.client = builder
                .baseUrl(baseUrl)
                .requestFactory(new SimpleClientHttpRequestFactory())
                .build();
        this.objectMapper = objectMapper;
    }

    @Override
    public AnalysisModels.PythonAnalysisResponse analyze(AnalysisModels.CreateAnalysisRequest request) {
        try {
            String payload = objectMapper.writeValueAsString(request);
            return client.post()
                    .uri("/analyses")
                    .contentType(MediaType.APPLICATION_JSON)
                    .accept(MediaType.APPLICATION_JSON)
                    .body(payload)
                    .retrieve()
                    .body(AnalysisModels.PythonAnalysisResponse.class);
        } catch (JsonProcessingException error) {
            throw new IllegalArgumentException("failed to serialize analysis request", error);
        }
    }

    @Override
    public AnalysisModels.PythonAnalysisResponse analyzeUpload(AnalysisModels.UploadAnalysisRequest request) {
        var multipart = new LinkedMultiValueMap<String, Object>();
        multipart.add("objective", request.objective());
        try {
            multipart.add("resultSchema", objectMapper.writeValueAsString(request.resultSchema()));
        } catch (JsonProcessingException error) {
            throw new IllegalArgumentException("failed to serialize result schema", error);
        }
        multipart.add("file", new ByteArrayResource(request.content()) {
            @Override
            public String getFilename() {
                return request.filename();
            }
        });
        return client.post()
                .uri("/analyses/upload")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .accept(MediaType.APPLICATION_JSON)
                .body(multipart)
                .retrieve()
                .body(AnalysisModels.PythonAnalysisResponse.class);
    }
}
