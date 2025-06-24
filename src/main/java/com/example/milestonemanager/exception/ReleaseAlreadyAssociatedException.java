package com.example.milestonemanager.exception;

public class ReleaseAlreadyAssociatedException extends RuntimeException {
    public ReleaseAlreadyAssociatedException(String message) {
        super(message);
    }
}