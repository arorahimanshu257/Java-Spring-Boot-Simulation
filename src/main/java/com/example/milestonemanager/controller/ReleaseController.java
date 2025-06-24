package com.example.milestonemanager.controller;

import com.example.milestonemanager.service.ReleaseService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/releases")
@RequiredArgsConstructor
public class ReleaseController {
    private final ReleaseService releaseService;

    @PostMapping("/{releaseId}/milestone/{milestoneId}")
    public ResponseEntity<Void> associateReleaseWithMilestone(@PathVariable Long releaseId, @PathVariable Long milestoneId) {
        releaseService.associateReleaseWithMilestone(releaseId, milestoneId);
        return new ResponseEntity<>(HttpStatus.NO_CONTENT);
    }
}