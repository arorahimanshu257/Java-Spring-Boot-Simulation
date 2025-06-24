package com.example.project.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.Set;

@Data
@Schema(description = "Request DTO for associating releases with a milestone")
public class ReleaseAssociationRequest {
    @NotNull
    @Schema(description = "Milestone ID to associate releases with", example = "1", required = true)
    private Long milestoneId;

    @NotEmpty
    @Schema(description = "Set of release IDs to associate", example = "[1, 2, 3]", required = true)
    private Set<Long> releaseIds;
}
