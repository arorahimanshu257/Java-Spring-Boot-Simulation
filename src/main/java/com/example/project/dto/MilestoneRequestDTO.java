package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.Set;

@Data
public class MilestoneRequestDTO {
    @NotBlank
    @Size(max = 100)
    @Schema(description = "Milestone name", example = "Alpha Release")
    private String name;

    @Size(max = 255)
    @Schema(description = "Milestone description", example = "Initial alpha release milestone")
    private String description;

    @NotNull
    @Future
    @Schema(description = "Milestone due date", example = "2024-12-31T23:59:59")
    private LocalDateTime dueDate;

    @Schema(description = "Associated release IDs")
    private Set<Long> releaseIds;
}
