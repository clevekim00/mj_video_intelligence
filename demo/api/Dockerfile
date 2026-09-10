FROM gradle:8.14.3-jdk21 AS build
WORKDIR /app
COPY demo/api/settings.gradle.kts demo/api/build.gradle.kts demo/api/gradle.properties ./
COPY demo/api/src ./src
RUN gradle --no-daemon bootJar

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/video-intelligence-demo-api-0.1.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
