# -*- coding: utf-8 -*-

from worker.codeplex import app

@app.task(autoretry_for=(Exception,))
def get_source_code():
    result = True

    return result