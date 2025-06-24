package com.example.project.controller;

import com.example.project.dto.ReleaseMilestoneAssociationResponse;
import com.example.project.exception.ErrorResponse;
import com.example.project.service.ReleaseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Release API", description = "Operations related to releases and milestone associations")
@RestController
@RequestMapping("/api/v1/releases")
@RequiredArgsConstructor
public class ReleaseController {

    private final ReleaseService releaseService;

    @Operation(
        summary = "Associate a release with a milestone",
        description = "Associates the specified release with the given milestone.",
        responses = {
            @ApiResponse(
                responseCode = "200",
                description = "Release associated with milestone successfully",
                content = @Content(schema = @Schema(implementation = ReleaseMilestoneAssociationResponse.class))
            ),
            @ApiResponse(
                responseCode = "400",
                description = "Invalid input",
                content = @Content(schema = @Schema(implementation = ErrorResponse.class))
            ),
            @ApiResponse(
                responseCode = "404",
                description = "Release or milestone not found",
                content = @Content(schema = @Schema(implementation = ErrorResponse.class))
            ),
            @ApiResponse(
                responseCode = "500",
                description = "Internal server error",
                content = @Content(schema = @Schema(implementation = ErrorResponse.class))
            )
        }
    )
    @PostMapping("/{releaseId}/milestone/{milestoneId}")
    public ResponseEntity<ReleaseMilestoneAssociationResponse> associateReleaseWithMilestone(
            @PathVariable("releaseId") @NotBlank String releaseId,
            @PathVariable("milestoneId") @NotBlank String milestoneId) {
        ReleaseMilestoneAssociationResponse response = releaseService.associateWithMilestone(releaseId, milestoneId);
        return ResponseEntity.status(HttpStatus.OK).body(response);
    }
}
