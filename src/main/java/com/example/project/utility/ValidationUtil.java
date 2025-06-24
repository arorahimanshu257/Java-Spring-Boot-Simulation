package com.example.project.utility;

import com.example.project.entity.Milestone;
import com.example.project.entity.Release;
import com.example.project.exception.ValidationException;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.time.LocalDate;

@Component
public class ValidationUtil {
    public void validateMilestone(Milestone milestone) {
        if (!StringUtils.hasText(milestone.getName())) {
            throw new ValidationException("Milestone name must not be empty");
        }
        if (milestone.getDueDate() == null) {
            throw new ValidationException("Milestone due date must not be null");
        }
        if (milestone.getDueDate().isBefore(LocalDate.now())) {
            throw new ValidationException("Milestone due date must be in the future");
        }
    }

    public void validateRelease(Release release) {
        if (!StringUtils.hasText(release.getVersion())) {
            throw new ValidationException("Release version must not be empty");
        }
        if (!StringUtils.hasText(release.getDescription())) {
            throw new ValidationException("Release description must not be empty");
        }
    }
}