package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Set;

@Data
public class MilestoneResponseDTO {
    @Schema(description = "Milestone ID", example = "1")
    private Long id;

    @Schema(description = "Milestone name", example = "Alpha Release")
    private String name;

    @Schema(description = "Milestone description", example = "Initial alpha release milestone")
    private String description;

    @Schema(description = "Milestone due date", example = "2024-12-31T23:59:59")
    private LocalDateTime dueDate;

    @Schema(description = "Associated releases")
    private Set<ReleaseSummaryDTO> releases;

    @Schema(description = "Milestone creation timestamp")
    private LocalDateTime createdAt;

    @Schema(description = "Milestone last update timestamp")
    private LocalDateTime updatedAt;
}
