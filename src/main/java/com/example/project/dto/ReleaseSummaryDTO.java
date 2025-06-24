package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ReleaseSummaryDTO {
    @Schema(description = "Release ID", example = "1")
    private Long id;

    @Schema(description = "Release version", example = "v1.0.0")
    private String version;

    @Schema(description = "Release date", example = "2024-11-01T10:00:00")
    private LocalDateTime releaseDate;
}
