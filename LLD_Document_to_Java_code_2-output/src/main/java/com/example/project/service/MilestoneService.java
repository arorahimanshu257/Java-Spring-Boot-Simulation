package com.example.project.service;

import com.example.project.entity.Milestone;
import com.example.project.exception.DuplicateMilestoneTitleException;
import com.example.project.exception.InvalidMilestoneDatesException;
import java.util.List;

public interface MilestoneService {
    Milestone createMilestone(Milestone milestone) throws DuplicateMilestoneTitleException, InvalidMilestoneDatesException;
    List<Milestone> getMilestonesByProjectId(String projectId);
    Milestone getMilestoneById(String milestoneId);
    void deleteMilestone(String milestoneId);
}