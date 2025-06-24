package com.example.project.controller;

import com.example.project.dto.MilestoneCreateRequest;
import com.example.project.dto.MilestoneResponse;
import com.example.project.exception.ErrorResponse;
import com.example.project.service.MilestoneService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.parameters.RequestBody;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody as SpringRequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Milestone API", description = "Operations related to milestones")
@RestController
@RequestMapping("/api/v1/milestones")
@RequiredArgsConstructor
public class MilestoneController {

    private final MilestoneService milestoneService;

    @Operation(
        summary = "Create a new milestone",
        description = "Creates a new milestone with the provided details.",
        requestBody = @RequestBody(
            required = true,
            content = @Content(schema = @Schema(implementation = MilestoneCreateRequest.class))
        ),
        responses = {
            @ApiResponse(
                responseCode = "201",
                description = "Milestone created successfully",
                content = @Content(schema = @Schema(implementation = MilestoneResponse.class))
            ),
            @ApiResponse(
                responseCode = "400",
                description = "Invalid input",
                content = @Content(schema = @Schema(implementation = ErrorResponse.class))
            ),
            @ApiResponse(
                responseCode = "500",
                description = "Internal server error",
                content = @Content(schema = @Schema(implementation = ErrorResponse.class))
            )
        }
    )
    @PostMapping
    public ResponseEntity<MilestoneResponse> createMilestone(
            @Valid @SpringRequestBody MilestoneCreateRequest request) {
        MilestoneResponse response = milestoneService.createMilestone(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}
