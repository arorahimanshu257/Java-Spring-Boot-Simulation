package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Set;

@Data
public class ReleaseResponseDTO {
    @Schema(description = "Release ID", example = "1")
    private Long id;

    @Schema(description = "Release version", example = "v1.0.0")
    private String version;

    @Schema(description = "Release description", example = "First major release")
    private String description;

    @Schema(description = "Release date", example = "2024-11-01T10:00:00")
    private LocalDateTime releaseDate;

    @Schema(description = "Associated milestone IDs")
    private Set<Long> milestoneIds;

    @Schema(description = "Release creation timestamp")
    private LocalDateTime createdAt;

    @Schema(description = "Release last update timestamp")
    private LocalDateTime updatedAt;
}
