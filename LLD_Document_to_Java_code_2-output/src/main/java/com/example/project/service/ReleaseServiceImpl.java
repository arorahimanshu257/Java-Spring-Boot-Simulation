package com.example.project.service;

import com.example.project.entity.Release;
import com.example.project.exception.DuplicateReleaseTagException;
import com.example.project.exception.InvalidReleaseDatesException;
import com.example.project.exception.ResourceNotFoundException;
import com.example.project.repository.ReleaseRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class ReleaseServiceImpl implements ReleaseService {

    private final ReleaseRepository releaseRepository;

    @Autowired
    public ReleaseServiceImpl(ReleaseRepository releaseRepository) {
        this.releaseRepository = releaseRepository;
    }

    @Override
    @Transactional
    public Release createRelease(Release release) throws DuplicateReleaseTagException, InvalidReleaseDatesException {
        // Validate unique tag within project
        boolean exists = releaseRepository.existsByTagAndProjectId(release.getTag(), release.getProjectId());
        if (exists) {
            throw new DuplicateReleaseTagException("Release tag must be unique within the project.");
        }
        // Validate startDate <= dueDate
        if (release.getStartDate() != null && release.getDueDate() != null && release.getStartDate().isAfter(release.getDueDate())) {
            throw new InvalidReleaseDatesException("Release startDate must be before or equal to dueDate.");
        }
        return releaseRepository.save(release);
    }

    @Override
    public List<Release> getReleasesByProjectId(String projectId) {
        return releaseRepository.findByProjectId(projectId);
    }

    @Override
    public Release getReleaseById(String releaseId) {
        return releaseRepository.findById(releaseId)
                .orElseThrow(() -> new ResourceNotFoundException("Release not found with id: " + releaseId));
    }

    @Override
    @Transactional
    public void deleteRelease(String releaseId) {
        if (!releaseRepository.existsById(releaseId)) {
            throw new ResourceNotFoundException("Release not found with id: " + releaseId);
        }
        releaseRepository.deleteById(releaseId);
    }
}
