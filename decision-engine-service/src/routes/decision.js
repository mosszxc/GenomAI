import express from 'express';
import { decisionEngine } from '../services/decisionEngine.js';
import { validateDecisionRequest } from '../utils/validators.js';

const router = express.Router();

// API Key authentication middleware
const authenticate = (req, res, next) => {
  const apiKey = req.headers.authorization?.replace('Bearer ', '');
  const expectedKey = process.env.API_KEY;

  if (!apiKey || apiKey !== expectedKey) {
    return res.status(401).json({
      success: false,
      error: {
        code: 'UNAUTHORIZED',
        message: 'Invalid or missing API key'
      }
    });
  }

  next();
};

// POST /api/decision
router.post('/', authenticate, async (req, res, next) => {
  try {
    // Validate request
    const validationError = validateDecisionRequest(req.body);
    if (validationError) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'INVALID_INPUT',
          message: validationError
        }
      });
    }

    // Make decision
    const result = await decisionEngine.makeDecision(req.body);

    // Return success response
    res.json({
      success: true,
      decision: result.decision,
      decision_trace: result.decisionTrace
    });
  } catch (error) {
    next(error);
  }
});

export default router;

