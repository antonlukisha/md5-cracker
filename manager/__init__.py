

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5005, debug=False)
    finally:
        retry_manager.stop()