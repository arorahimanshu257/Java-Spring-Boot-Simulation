package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Schema(description = "Request DTO for creating a milestone")
public class MilestoneCreateRequest {
    @NotBlank
    @Size(max = 100)
    @Schema(description = "Milestone name", example = "Alpha Release", required = true)
    private String name;

    @Size(max = 500)
    @Schema(description = "Milestone description", example = "Initial alpha release milestone")
    private String description;

    @NotNull
    @Future
    @Schema(description = "Due date for the milestone", example = "2024-12-31T23:59:59", required = true)
    private LocalDateTime dueDate;
}
