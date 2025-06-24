package com.example.project.controller;

import com.example.project.dto.MilestoneRequestDTO;
import com.example.project.dto.MilestoneResponseDTO;
import com.example.project.service.MilestoneService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/milestones")
@RequiredArgsConstructor
@Tag(name = "Milestones", description = "Milestone management APIs")
public class MilestoneController {

    private final MilestoneService milestoneService;

    @PostMapping
    @Operation(summary = "Create a new milestone")
    public ResponseEntity<MilestoneResponseDTO> createMilestone(@Valid @RequestBody MilestoneRequestDTO requestDTO) {
        MilestoneResponseDTO response = milestoneService.createMilestone(requestDTO);
        return new ResponseEntity<>(response, HttpStatus.CREATED);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get milestone by ID")
    public ResponseEntity<MilestoneResponseDTO> getMilestone(@PathVariable Long id) {
        MilestoneResponseDTO response = milestoneService.getMilestoneById(id);
        return ResponseEntity.ok(response);
    }

    @GetMapping
    @Operation(summary = "Get all milestones")
    public ResponseEntity<List<MilestoneResponseDTO>> getAllMilestones() {
        List<MilestoneResponseDTO> responses = milestoneService.getAllMilestones();
        return ResponseEntity.ok(responses);
    }

    @PutMapping("/{id}/releases")
    @Operation(summary = "Associate releases with a milestone")
    public ResponseEntity<MilestoneResponseDTO> associateReleases(
            @PathVariable Long id,
            @RequestBody List<Long> releaseIds) {
        MilestoneResponseDTO response = milestoneService.associateReleases(id, releaseIds);
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete a milestone by ID")
    public ResponseEntity<Void> deleteMilestone(@PathVariable Long id) {
        milestoneService.deleteMilestone(id);
        return ResponseEntity.noContent().build();
    }
}
