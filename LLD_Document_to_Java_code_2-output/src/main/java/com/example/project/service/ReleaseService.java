package com.example.project.service;

import com.example.project.entity.Release;
import com.example.project.exception.DuplicateReleaseTagException;
import com.example.project.exception.InvalidReleaseDatesException;
import java.util.List;

public interface ReleaseService {
    Release createRelease(Release release) throws DuplicateReleaseTagException, InvalidReleaseDatesException;
    List<Release> getReleasesByProjectId(String projectId);
    Release getReleaseById(String releaseId);
    void deleteRelease(String releaseId);
}