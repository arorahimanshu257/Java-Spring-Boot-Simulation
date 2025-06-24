package com.example.milestonemanager.exception;

public class ReleaseTagNotUniqueException extends RuntimeException {
    public ReleaseTagNotUniqueException(String message) {
        super(message);
    }
}